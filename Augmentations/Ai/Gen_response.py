from groq import AsyncGroq
import os
from Global import config
import asyncio
from Augmentations.Ai.Analize_image import analyze_image  # Import the analyze_image function

api_keys = [
    config['API_KEYS']['API_KEY_1'],
    config['API_KEYS']['API_KEY_2'],
    config['API_KEYS']['API_KEY_3'],
    config['API_KEYS']['API_KEY_4'],
    config['API_KEYS']['API_KEY_5'],
]

default_instructions = (
    "You are a Quint a discord bot, you are working in a confidential environment, "
    "keep your responses short and concise, and don't mention your name or mention the user "
    "unless it is necessary. Only answer relevant questions, and don't make up new information. "
    "If you don't know the answer, say so, and don't make up new information. Make sure your answers "
    "are within 100 characters only exceeding 100 characters when absolutely required."
)
clients = [AsyncGroq(api_key=key) for key in api_keys]
client_usage = {i: 0 for i in range(len(clients))}

async def gen_response(history, instructions=default_instructions, command_request=None, user_name=None, user_mention=None, image_data=None):
    messages = [
        {"role": "system", "content": instructions},
        *history,
    ]
    if user_name:
        messages.append({
            "role": "system",
            "name": "username",
            "content": f"user_name: {user_name} This is the name of the user."
        })
    if user_mention:
        messages.append({
            "role": "system",
            "name": "user_mention",
            "content": f"user_id : {user_mention} this is only required for executing commands, mainly the id.]"
        })
    if command_request:
        messages.append({
            "role": "system",
            "name": "command_info",
            "content": command_request
        })
    
    if image_data:
        image_analysis = await analyze_image(image_data)
        if image_analysis:
            messages.append({
                "role": "system",
                "content": f"An image was included in the message. Here's the analysis: {image_analysis.content}"
            })
    # Select the client with the least usage
    client_index = min(client_usage, key=client_usage.get)
    client = clients[client_index]
    client_usage[client_index] += 1

    # Call the Groq API with the constructed messages
    try:
        stream = await client.chat.completions.create(
            model=config['MODEL_ID'],
            messages=messages,
            temperature=0.9,
            max_tokens=8000,
            top_p=1,
            stream=True,
        )

        # Stream the response
        response_message = ""
        async for chunk in stream:
            try:
                if chunk.choices[0].delta.content is not None:
                    response_message += chunk.choices[0].delta.content
            except (AttributeError, IndexError) as e:
                print(f"Error during streaming: {e}")
                print(f"Chunk data: {chunk}")

        client_usage[client_index] -= 1
        return response_message
    except Exception as e:
        error_message = str(e)
        print(f"Failed to generate response: {error_message}")
        client_usage[client_index] -= 1

        # If rate limit is reached, try the next client
        if "Rate limit reached" in error_message:
            next_client_index = (client_index + 1) % len(clients)
            return await gen_response(history, instructions, command_request, user_name, user_mention, image_data)

        return "An error occurred while generating the response. Please try again later."