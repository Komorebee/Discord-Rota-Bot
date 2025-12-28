# Discord Rota Bot

A Discord bot that integrates with **Quinyx** to provide shift schedule information directly inside your server.

🛠️ Built with **Node.js**, **discord.js**, and the **Quinyx API**, this bot helps teams check shifts, bind Discord accounts to Quinyx, and automatically assign roles for members “currently on shift.”

## 🚀 Features

- 🔗 **Bind Discord to Quinyx**  
  `/iam` — link your Discord username to your Quinyx user.

- 📅 **Check Your Next Shift**  
  `/nextshift` — display your upcoming shift(s).

- 👥 **Team Rota Lookup**  
  `/whosworking` — show who is working today (and optionally until 3 AM).

- 🤖 **Auto Role Updates**  
  At 18:00 each day, assigns a “Currently On Shift” role to users working and removes it when their shift ends.

---

## 📦 Requirements

Before installing:

- **Node.js** 18+  
- A **Discord Bot Token**  
- Access to a **Quinyx API** with credentials  
- A server where you can register slash commands

---

## ⚙️ Setup and Installation

1. **Clone this repository**
   ```bash
   git clone https://github.com/Komorebee/Discord-Rota-Bot.git
   cd Discord-Rota-Bot
Install dependencies

bash
Copy code
npm install
Create the .env file
Copy .env.example to .env and populate with your keys:

env
Copy code
DISCORD_TOKEN=your_discord_bot_token
CLIENT_ID=your_discord_application_id
GUILD_ID=your_test_guild_id
QUINYX_CLIENT_ID=quinyx_api_client_id
QUINYX_CLIENT_SECRET=quinyx_api_client_secret
QUINYX_TENANT=your_quinyx_tenant
Register slash commands

bash
Copy code
npm run register-commands
Start the bot

bash
Copy code
npm start
🧠 Bot Commands
Slash Command	Description
/iam	Link your Discord user to your Quinyx username
/nextshift	Show your next scheduled shift
/nextshift @user	(Optional) Show another user’s next shift
/whosworking	List today’s shift roster until 3 AM

📅 Workflow and Behavior
When a user runs /iam, they bind their Discord ID to a Quinyx account in the bot database.

/nextshift pulls Quinyx schedule data for the linked user and shows their next shift in Discord.

/whosworking queries Quinyx for users scheduled today and displays them sorted by start time.

A scheduled job runs daily at 18:00 local time to:

Add “Currently On Shift” role to users whose shift is happening now.

Remove the role when the shift ends.

🧪 Local Development Tips
Use nodemon for auto-restart during edits:

bash
Copy code
npm install -D nodemon
nodemon
Use a test Discord server (GUILD_ID) to avoid spamming production with incomplete commands.

Log responses when integrating with the Quinyx API to ensure correct data shape.

🧩 Project Structure
graphql
Copy code
.
├── commands/             # Slash command handlers
├── events/               # Discord event listeners
├── services/             # Quinyx API logic & scheduling
├── utils/                # Helper functions
├── .env.example
├── index.js              # Bot entry point
├── package.json
└── README.md
🤝 Contributing
Contributions are welcome! Here’s how to help:

Fork the repository

Create a feature branch

css
Copy code
git checkout -b feature/<your-feature>
Commit your changes

Open a pull request

Please include tests where possible and follow existing style patterns.

📜 License
This project is open-source under the MIT License.

📌 Contact
Created by Ashraf Jamel
Feel free to reach out if you want help deploying this bot or extending it for workplace automation.
