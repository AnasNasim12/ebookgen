from dotenv import load_dotenv
load_dotenv()
# from outlinemaker import outline_prompt
import os
import google.generativeai as genai
import json

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
            
    print(all_subtopics)

outline_prompt("The Art of War", "military strategy", "military leaders", 5, 4)

