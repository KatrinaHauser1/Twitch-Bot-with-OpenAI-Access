# Twitch-Bot-with-OpenAI-Access
Creates a functioning twitch bot that can send prompts and receive answers from OpenAI 
SETUP CREDITS: twitchio.dev

Sample Usage:
- !ask whats 5+5?
- 5 + 5 equals 10! 😊 Do you have any other questions?

- @twitch_bot_2610 give me fun facts about atlanta
- Sure! Here are some fun facts about Atlanta: 1. Atlanta is known as the "City in a Forest" because it has tons of trees—over 40% of the city is wooded! 2. It’s home to Coca-Cola! The World of Coca-Cola museum showcases the history and variety of this iconic drink. 3. Atlanta played a key role in the Civil Rights Movement, with important sites like the Martin Luther King Jr. National Historical Park. 

STEPS FOR SETUP:
- follow the initial setups steps at twitchio.dev/en/latest/getting-started/quickstart.html to get the twitch bot online/authorized
- run pip install openai inside your virtual environment
- go to openai.com, sign up/log in, and get a API KEY and save it
- run export OPENAI_API_KEY="your_key_here" in your virtual environment
- tailor your bot, especially the initial setup prompt
- !!OPTIONAL: to have the LLM respond to every message that pings the bot, uncomment the commented lines in event_message
- customize commands and talk to the bot in any twitch chat you want :)
