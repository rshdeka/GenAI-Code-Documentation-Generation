import logging  
import os
import chardet  
from github import Github, GithubException  
from OpenAI import callGptEndpoint  
  

logging.basicConfig(level=logging.INFO)  


# Retrieve all code files from a given GitHub repository  
def get_code_files(repo_name, access_token):  
    try:  
        # Authenticate with GitHub using the provided access token  
        g = Github(access_token)  
        repo = g.get_repo(repo_name)  
          
        # Get the contents of the root directory of the repository  
        contents = repo.get_contents("")  
        file_count = 0
        while contents:  
            # Get the first item from the contents list 
            file_content = contents.pop(0)  
            # If the item is a directory, extend the contents list with its contents  
            if file_content.type == "dir":  
                contents.extend(repo.get_contents(file_content.path))  
            else:            # Else, get the file path  
                file_path = file_content.path  
                if file_path.lower().endswith(('.png', '.jpg', '.jpeg', '.gif', '.ico', '.bmp', '.jfif', '.woff', '.woff2', '.env', '.venv', '.gitignore', '.md')):  
                    continue  
                try:  
                    # Retrieve the file content  
                    file_content_data = repo.get_contents(file_path).decoded_content  
                    detected_encoding = chardet.detect(file_content_data)['encoding']  
                    file_content_data = file_content_data.decode(detected_encoding)  
                    file_count += 1
                    # Return a generator to yield the file path and content one at a time  
                    yield (file_path, file_content_data)  
                except Exception as e:  
                    logging.warning(f"Skipping file {file_path} due to decoding error: {str(e)}")  
        logging.info(f"Total number of files to process: {file_count}")
    except GithubException as e:  
        logging.error(f"GitHub Exception: {str(e)}")  
    except Exception as e:  
        logging.error(f"Exception: {str(e)}")  
  

# GPT prompt  
def create_gpt_prompt(file_path, content):
    prompt = f'''
    Generate a well-structured and detailed rundown of the code in each of the following files in Markdown format. 
    For each function within a file, format the output as follows:\n 
    **File: {file_path}**
    **Summary**: [a very comprehensive and detailed description what the code in this file does.]
    **Functions**:
        1. [function_name()]  
            - Purpose: [purpose of the function] 
            - Summary: [a very comprehensive and detailed description of the function's {content}]  
    '''
    return prompt
 
  
# Call GPT and generate documentation for the given prompt  
def call_gpt_and_generate_documentation(prompt):  
    user_message = {  
        "role": "user",  
        "content": prompt  
    }  
  
    messages = [user_message]  
    gpt_options = {
        "engine": os.environ["AZURE_OPENAI_MODEL"],  
        "messages": messages,  
        "temperature": 0,  
        "max_tokens": 4096
    }
  
    gpt_response = callGptEndpoint(gpt_options)

    if str(gpt_response).startswith("Unexpected"):  
        logging.error("Error occurred while calling GPT endpoint.")  
   
    # Extract the generated content and token usage 
    generated_doc = gpt_response.choices[0].message.content
    prompt_tokens = gpt_response.usage.prompt_tokens
    completion_tokens = gpt_response.usage.completion_tokens
    total_tokens = gpt_response.usage.total_tokens
    logging.info("GPT response processed successfully.")

    return (generated_doc, prompt_tokens, completion_tokens, total_tokens)


# Update the existing documentation  
def update_documentation(documentation, new_content):
    # Combine the existing documentation with the new content  
    updated_documentation = documentation + "\n\n" + new_content  
    return updated_documentation


# Process files from the GitHub repository individually and send them to the GPT model
def process_files_individually(repo_name, access_token):
    file_count = 0                  # Initialize file counter

    # Initialize documentation content  
    documentation_content = ""

    # Initialize Postman response string
    postman_response = "" 

    for file_path, file_content in get_code_files(repo_name, access_token):
        logging.info(f"Processing file: {file_path}")
        file_count += 1

        # Generate GPT prompt for the file
        file_prompt = create_gpt_prompt(file_path, file_content)

        try:  
            # Call GPT and generate documentation for the file  
            file_documentation, prompt_tokens, completion_tokens, total_tokens = call_gpt_and_generate_documentation(file_prompt)  
            logging.info(f"\nDocumentation generated for file: {file_path}")  
              
            # Update the documentation content  
            documentation_content = update_documentation(documentation_content, file_documentation)

            # Append to postman response  
            postman_response += (  
                f"\nDOCUMENTATION GENERATED FOR FILE: {file_path}\n"  
                f"Total Tokens: {total_tokens}\n"  
                f"Prompt Tokens: {prompt_tokens}\n"  
                f"Completion Tokens: {completion_tokens}\n"  
            )
        except Exception as e:
            logging.error(f"Exception for file {file_path}: {str(e)}")
        
    # Save the generated documentation to a file
    filename = "documentation.md"  
    with open(filename, "w") as f:  
        f.write(documentation_content)

    # Include the file count in the Postman response
    res = f"Total number of files processed: {file_count} \n{{{postman_response}}}"
    return res


def main():
    logging.info('Generating documentation for GitHub repository.')

    try:
        # Fetch the GitHub repository name and access token from env variables  
        repo_name = "rshdeka/UI-Testing-Automation-PoC"
        access_token = os.environ["GITHUB_TOKEN"]
        event_type = os.environ["EVENT_TYPE"]

        if event_type == "pull_request":  
            pr_number = int(os.environ["PR_NUMBER"])  
            pr = Github(access_token).get_repo(repo_name).get_pull(pr_number)  
            pr_branch_ref = pr.head.ref

            # Process files individually and generate documentation for PR  
            logging.info(f"Processing files for pull request #{pr_number} on branch {pr_branch_ref}")  
            res = process_files_individually(repo_name, access_token)  
            logging.info(res)  
  
        elif event_type == "push":  
            pr_branch_ref = os.environ["GITHUB_REF"].replace("refs/heads/", "")  
  
            # Process files individually and generate documentation for push  
            logging.info(f"Processing files for push event on branch {pr_branch_ref}")  
            res = process_files_individually(repo_name, access_token)  
            logging.info(res)

    except Exception as e:  
        logging.error(f"Error: {str(e)}")
    

if __name__ == "__main__":   
    main() 