import streamlit as st
import base64
from datetime import datetime
from dotenv import load_dotenv
load_dotenv()
from geminiconfig import safety_settings
import os
import google.generativeai as genai
import json
import markdown
from weasyprint import HTML
import PyPDF2
import torch
from diffusers import AmusedPipeline
from PIL import Image
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter

genai.configure(api_key=os.getenv('GOOGLE_API_KEY'))
model = genai.GenerativeModel("gemini-pro")

def outline_prompt(title, topic, target_audience, num_chapters, num_subsections):
    outlineprompt = (
    f'We are writing an eBook called "{title}". It is about'
    f' "{topic}". Our reader is: {target_audience}". Create'
    " a compehensive outline for our ebook, which will have"
    f" {num_chapters} chapter(s). Each chapter should have exactly"
    f" {num_subsections} subsection(s)"
    f'Output format for prompt:'
    f'python dict with key: chapter title, value: a single list/array Please refrain from adding any unnecessary formatting elements like code blocks or indentation in the output.'
    f'Containing subsection titles within the chapter with numbering (the subtopics should be inside the list)')
    response = model.generate_content(outlineprompt)
    # Parse the generated content as JSON
    try:
        dictionary = json.loads(response.text)
    except json.JSONDecodeError:
        print("Error: Could not decode JSON")
        return False
    
    all_subtopics = []
    for chapter, subtopics in dictionary.items():
        all_subtopics.extend(subtopics)  # Add subtopics to the list

        if isinstance(subtopics, dict):
            all_subtopics.extend(get_all_subtopics(subtopics))  # Recursive call for nested chapters

    with open("contents.md", 'w') as file:
       for chapter, subtopics in dictionary.items():
          file.write(f"## {chapter}\n")  # Write chapter title with newline
          for subtopic in subtopics:
             file.write(f"#### {subtopic}\n")  # Write subtopic with newline

    page_prompt = (f'We are writing an eBook called "{title}". It is about'
    f' "{topic}". Our reader is: {target_audience}".'
    f'You will be given a topic and you must generate detailed text of atleast 400 words, keeping in mind the topic {topic} and target audience {target_audience}'
    f'Output format for prompt:'
    f'Detailed text, nuanced text, informative. Keep the output as long as possible. Make sure you follow proper markdown formatting for headings and such. In case of code snippets, keep proper markdown formatting'
    f'It is of utmost importance that the formatting is right!'
    f'Imagine you are writing a page for the book, your text should be written in a way that the target audience understands it with ease. Make sure that the content you generate is continuous and cohesive'
    f'So in case you are writing a story, you must maintain continuity. Stories do not need a conclusion section. You must write out the topic name at the beginning of the page.'
    f'Topic is as follows:')

    all_text = ""
    if all_subtopics is not None:
        for subtopic in all_subtopics:
            page = model.generate_content(page_prompt + subtopic, safety_settings=safety_settings)
            all_text += page.text + "\n\n"
        with open("ebook.md", "a") as f:
            f.write(all_text)
    else:
        print("Chapter not found in the dictionary.")
    
    return True

def pdfmaker(markdown_file_path, pdf_file_path):
    with open(markdown_file_path, 'r', encoding='utf-8', errors='ignore') as md_file:
        markdown_text = md_file.read()
        html_text = markdown.markdown(markdown_text)
        HTML(string=html_text).write_pdf(pdf_file_path)
    print(f'PDF has been generated: {pdf_file_path}')

def merge_pdfs(pdf_file_path1, pdf_file_path2, merged_file_path):
    # Open the PDF files
    with open(pdf_file_path1, 'rb') as pdf1_file, open(pdf_file_path2, 'rb') as pdf2_file:
        # Create PDF reader objects for each file
        pdf1_reader = PyPDF2.PdfReader(pdf1_file)
        pdf2_reader = PyPDF2.PdfReader(pdf2_file)

        # Create a PDF writer object for the output file
        pdf_writer = PyPDF2.PdfWriter()

        # Add all pages from the first PDF
        for page_num in range(len(pdf1_reader.pages)):
            page = pdf1_reader.pages[page_num]
            pdf_writer.add_page(page)

        # Add all pages from the second PDF
        for page_num in range(len(pdf2_reader.pages)):
            page = pdf2_reader.pages[page_num]
            pdf_writer.add_page(page)

        # Write to the new PDF file
        with open(merged_file_path, 'wb') as merged_file:
            pdf_writer.write(merged_file)

    print(f'PDF files have been merged into {merged_file_path}')

def generate_and_save_image(prompt, image_path, negative_prompt="low quality, ugly"):
    # Initialize the pipeline
    pipe = AmusedPipeline.from_pretrained(
        "amused/amused-512"
    )
    pipe = pipe.to("cpu")
    
    # Generate the image
    image = pipe(prompt, negative_prompt=negative_prompt, generator=torch.manual_seed(0)).images[0]
    
    # Save the image to a file
    image.save(image_path)
    
    print(f"Image saved to {image_path}")

def create_pdf_title_page(image_path, output_pdf, title):

    # Open the image to get its size
    img = Image.open(image_path)
    img_width, img_height = img.size

    # Calculate the PDF page size in pixels (converting from points: 1 point = 1/72 inch)
    pdf_width, pdf_height = letter  # in points
    scale_w = pdf_width / img_width
    scale_h = pdf_height / img_height
    scale = min(scale_w, scale_h)

    # Create a new canvas and draw the image
    c = canvas.Canvas(output_pdf, pagesize=letter)
    c.drawImage(image_path, 0, 0, width=pdf_width, height=pdf_height, preserveAspectRatio=True, mask='auto')

    # Add the title text on top of the image
    c.setFont("Helvetica", 26)  # Using a default font
    c.drawCentredString(pdf_width / 2, pdf_height - 50, title)  # Adjust positioning as needed

    # Save the PDF
    c.save()

    print(f"PDF saved as {output_pdf}")

def cleanup(files):
    for file_path in files:
        try:
            os.remove(file_path)
            print(f"Deleted {file_path}")
        except OSError as e:
            print(f"Error: {file_path} : {e.strerror}")

def generate_unique_filename(base_name, extension):
    current_time = datetime.now().strftime("%Y%m%d%H%M%S")
    return f"{base_name}_{current_time}.{extension}"

def get_user_input():
    title = st.text_input("Enter the eBook title: ")
    topic = st.text_input("Enter the eBook topic: ")
    target_audience = st.text_input("Enter the target audience: ")
    num_chapters = st.number_input("Enter the number of chapters: ")
    num_subsections = st.number_input("Enter the number of subsections per chapter: ")
    return title, topic, target_audience, num_chapters, num_subsections

def main():
    st.title("eBook Generator")
    
    title, topic, target_audience, num_chapters, num_subsections = get_user_input()
    
    if st.button("Generate eBook"):
        if title and topic and target_audience and num_chapters > 0 and num_subsections > 0:
            success = outline_prompt(title, topic, target_audience, num_chapters, num_subsections)
            if not success:
                st.error("Failed to generate the eBook outline. Please try again.")
                return
            
            # Generate a unique filename for this run
            final_ebook_filename = generate_unique_filename("final_eBook", "pdf")
            
            pdfmaker("contents.md", "contents.pdf")
            pdfmaker("ebook.md", "ebook.pdf")
            merge_pdfs('contents.pdf', 'ebook.pdf', 'merged_pdf.pdf')
            generate_and_save_image(title, "generated_pic.png")
            create_pdf_title_page('generated_pic.png', 'output_title_page.pdf', title)
            merge_pdfs('output_title_page.pdf', 'merged_pdf.pdf', final_ebook_filename)
            
            with open(final_ebook_filename, 'rb') as pdf_file:
                base64_pdf = base64.b64encode(pdf_file.read()).decode('utf-8')
            pdf_display = f'<iframe src="data:application/pdf;base64,{base64_pdf}" width="700" height="1000" type="application/pdf"></iframe>'
            st.markdown(pdf_display, unsafe_allow_html=True)
            st.download_button(label="Download eBook", data=open(final_ebook_filename, 'rb'), file_name=final_ebook_filename, mime='application/pdf')
            st.success("eBook generated successfully!")
            
            # Cleanup intermediate files
            cleanup(['contents.md', 'contents.pdf', 'ebook.md', 'ebook.pdf', 'merged_pdf.pdf', 'generated_pic.png', 'output_title_page.pdf'])
        else:
            st.error("Please fill in all the fields and ensure the number of chapters and subsections are greater than 0.")

if __name__ == "__main__":
    main()
