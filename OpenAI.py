import logging
import os
from openai import AzureOpenAI
from dotenv import load_dotenv

load_dotenv()

client = AzureOpenAI(
    api_key=os.environ["AZURE_OPENAI_KEY"],
    azure_endpoint=os.environ['AZURE_OPENAI_API_BASE'],
    api_version=os.environ['AZURE_OPENAI_API_VERSION']   
)

def callGptEndpoint(gptOptions):  
    try:  
        logging.info('GPT endpoint call initiating with engine %s',  str(gptOptions['engine']))
        
        response = client.with_options(max_retries=5).chat.completions.create(    
            model=gptOptions['engine'],    
            messages=gptOptions['messages'],    
            temperature=gptOptions['temperature'],    
            max_tokens=gptOptions['max_tokens']
        )

        logging.info('GPT endpoint call successful with engine %s',  str(gptOptions['engine']))
        logging.info(type(response))
        
        #return response.choices[0].message.content
        return response
    
    except Exception as e:   
        logging.info('Unexpected error calling GPT endpoint:   %s',  str(e))
        # return 'Unexpected error calling GPT endpoint: '+str(e)
        raise e