import datetime
import os
from typing import Any, List, Tuple

import uvicorn
from dotenv import load_dotenv
from openai import OpenAI
from pinecone import Pinecone
from pydantic import BaseModel

from fastapi import FastAPI

app = FastAPI()
load_dotenv()

pinecone_key = os.environ.get('PINECONE_API_KEY')
INDEX_NAME = 'semantic-search-rag'
ENGINE = 'text-embedding-3-small'
NAMESPACE = 'default'

pc = Pinecone(
    api_key=pinecone_key
)
client = OpenAI(api_key=os.environ.get('OPENAI_API_KEY'))
index = pc.Index(name=INDEX_NAME)


def query_from_pinecone(query, top_k=1, include_metadata=True):
    # get embedding from THE SAME embedder as the documents
    query_embedding = get_embedding(query, engine=ENGINE)

    return index.query(
        vector=query_embedding,
        top_k=top_k,
        namespace=NAMESPACE,
        include_metadata=include_metadata  # gets the metadata (dates, text, etc)
    ).get('matches')


# helper functions to get lists of embeddings from the OpenAI API
def get_embedding(text, engine=ENGINE):
    response = client.embeddings.create(
        input=[text],
        model=engine
    )
    return response.data[0].embedding


conversations = {}


# Define a class for the Chat Language Model
class OpenAIChatLLM(BaseModel):
    model: str = 'gpt-4o'  # Default model to use
    temperature: float = 0.0  # Default temperature for generating responses

    # Method to generate a response from the model based on the provided prompt
    def generate(self, prompt: str, stop: List[str] = None):
        # Create a completion request to the OpenAI API with the given parameters
        response = client.chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
            temperature=self.temperature,
            stop=stop
        )

        # Return the generated response content
        return response.choices[0].message.content


FINAL_ANSWER_TOKEN = "Assistant Response:"
STOP = '[END]'
PROMPT_TEMPLATE = """Today is {today} and you can retrieve information from a database. Respond to the user's input as best as you can.

Here is an example of the conversation format:

[START]
User Input: the input question you must answer
Context: retrieved context from the database
Context URL: context url
Context Score : a score from 0 - 1 of how strong the information is a match
Assistant Thought: This context has sufficient information to answer the question.
Assistant Response: your final answer to the original input question which could be I don't have sufficient information to answer the question.
[END]
[START]
User Input: another input question you must answer
Context: more retrieved context from the database
Context URL: context url
Context Score : another score from 0 - 1 of how strong the information is a match
Assistant Thought: This context does not have sufficient information to answer the question.
Assistant Response: your final answer to the second input question which could be I don't have sufficient information to answer the question.
[END]
[START]
User Input: another input question you must answer
Context: more retrieved context from the database
Context URL: context url
Context Score : another score from 0 - 1 of how strong the information is a match
Assistant Thought: A previous piece of context has the answer to this question
Assistant Response: your final answer to the second input question which could be I don't have sufficient information to answer the question.
[END]
[START]
User Input: another input question you must answer
Context: NO CONTEXT FOUND
Context URL: NONE
Context Score : 0
Assistant Thought: We either could not find something or we don't need to look something up
Assistant Response: I'm sorry I don't know.
[END]

Begin:

{running_convo}
"""


class RagBot(BaseModel):
    llm: Any
    prompt_template: str = PROMPT_TEMPLATE
    stop_pattern: List[str] = [STOP]
    user_inputs: List[str] = []
    ai_responses: List[str] = []
    contexts: List[Tuple[str, float]] = []
    verbose: bool = False
    threshold: float = 0.5

    def query_from_pinecone(self, query, top_k=1, include_metadata=True):
        return query_from_pinecone(query, top_k, include_metadata)

    @property
    def running_convo(self):
        convo = ''
        for index in range(len(self.user_inputs)):
            convo += f'[START]\nUser Input: {self.user_inputs[index]}\n'
            convo += f'Context: {self.contexts[index][0]}\nContext URL: {self.contexts[index][1]}\nContext Score: {self.contexts[index][2]}\n'
            if len(self.ai_responses) > index:
                convo += self.ai_responses[index]
                convo += '\n[END]\n'
        return convo.strip()

    def run(self, question: str):
        self.user_inputs.append(question)
        top_response = self.query_from_pinecone(question)[0]
        if self.verbose:
            print(top_response['score'])
        if top_response['score'] >= self.threshold:
            self.contexts.append(
                (top_response['metadata']['text'], top_response['metadata']['url'], top_response['score']))
        else:
            self.contexts.append(('NO CONTEXT FOUND', 'NONE', 0))

        prompt = self.prompt_template.format(  # behold, the augmentation
            today=datetime.date.today(),
            running_convo=self.running_convo
        )
        if self.verbose:
            print('--------')
            print('PROMPT')
            print('--------')
            print(prompt)
            print('--------')
            print('END PROMPT')
            print('--------')
        generated = self.llm.generate(prompt, stop=self.stop_pattern)
        if self.verbose:
            print('--------')
            print('GENERATED')
            print('--------')
            print(generated)
            print('--------')
            print('END GENERATED')
            print('--------')
        self.ai_responses.append(generated)
        if FINAL_ANSWER_TOKEN in generated:
            generated = generated.split(FINAL_ANSWER_TOKEN)[-1]
        return generated


class ConversationRequest(BaseModel):
    text: str
    temperature: float = 0.1
    threshold: float = 0.3
    namespace: str = "default"
    conversation_id: str = None


class ConversationResponse(BaseModel):
    response: str
    conversation_id: str


@app.post("/process_text", response_model=ConversationResponse)
async def conversation(request: ConversationRequest):
    message = request.text
    temperature = request.temperature
    threshold = request.threshold
    print('Conversation id:', request.conversation_id)
    # Generate a new conversation_id if not provided
    if request.conversation_id is None:
        request.conversation_id = str(uuid.uuid4())

    if request.conversation_id not in conversations:
        conversations[request.conversation_id] = RagBot(
            llm=OpenAIChatLLM(
                temperature=temperature, model='gpt-4o'), stop_pattern=['[END]'], verbose=True,
            threshold=threshold)
    bot = conversations[request.conversation_id]
    response = bot.run(message)

    return ConversationResponse(response=response, conversation_id=request.conversation_id)


if __name__ == "__main__":
    uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=True)
