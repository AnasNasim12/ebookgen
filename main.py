from dotenv import load_dotenv
load_dotenv()
# from outlinemaker import outline_prompt
import os
import google.generativeai as genai
import json
import markdown
from weasyprint import HTML


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
    f'Containing subsection titles within the chapter (the subtopics should be inside the list)')
    response = model.generate_content(outlineprompt)
    # Parse the generated content as JSON
    try:
        dictionary = json.loads(response.text)
    except json.JSONDecodeError:
        print("Error: Could not decode JSON")
        return None
    
    all_subtopics = []
    for chapter, subtopics in dictionary.items():
        all_subtopics.extend(subtopics)  # Add subtopics to the list

        if isinstance(subtopics, dict):
            all_subtopics.extend(get_all_subtopics(subtopics))  # Recursive call for nested chapters

    with open("contents.md", 'w') as file:
       for chapter, subtopics in dictionary.items():
          file.write(f"## {chapter}\n")  # Write chapter title with newline
          for subtopic in subtopics:
             file.write(f"- #### {subtopic}\n")  # Write subtopic with newline

    return all_subtopics
    # print(dictionary)
outline_prompt("The 2nd World War", "Germany in 1945", "pre-school kids", 5, 2)

def pdfmaker(markdown_file_path, pdf_file_path):
    with open(markdown_file_path, 'r', encoding='utf-8') as md_file:
        markdown_text = md_file.read()
        html_text = markdown.markdown(markdown_text)
        HTML(string=html_text).write_pdf(pdf_file_path)
    print(f'PDF has been generated: {pdf_file_path}')

pdfmaker("contents.md", "contents.pdf")
