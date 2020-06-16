# Fish seller bot

This project contains code for creation your bot, which has a shop functionality.

Bot integrated with Redis DB.

### How to install

##### Local

You need to create `.env` file and write next parameters in file:

`TG_BOT_TOKEN` - secret telegram bot token. Use [this](https://core.telegram.org/bots#creating-a-new-bot) instruction (use VPN to open this link in Russia).

After you got `TG_BOT_TOKEN` you need to write to you telegram bot any message (`/start` for example).
    
`ELASTICPATH_CLIENT_ID` - ID of your shop in [elasticpath](https://dashboard.elasticpath.com/app)

`PROXY` - proxy IP with port and https if you need. Work with empty proxy if you in Europe.

`REDIS_DB_ADDRESS` - register your [redis](https://redislabs.com/) account and get address of your database (for example `redis-13965.f18.us-east-4-9.wc1.cloud.redislabs.com`).

`REDIS_DB_PORT` - usually port writes in db address in the end `redis-13965.f18.us-east-4-9.wc1.cloud.redislabs.com:16635`

`REDIS_DB_PASSWORD` - redis also will generate your DB password when your will init DB.

Python3 should be already installed. 
Then use `pip` (or `pip3`, if there is a conflict with Python2) to install dependencies:
```
pip install -r requirements.txt
```

##### Deploy on heroku

For deploying this bot on [heroku](https://heroku.com) you need to do next:

1) Sign up in heroku
2) Create app
3) Clone this repository and download on heroku with GitHub method (tab `Deploy` in heroku app)
    
### How to use

##### Run in Local

Open command line (in windows `Win+R` and write `cmd` and `Ok`). Go to directory with program or write in cmd:

```
python tg_bot.py 
```

##### Deploy on heroku

Run bot in `Resources` tab in heroku app. `Procfile` for run in repo already.

### References

- [telegram bots documentation](https://core.telegram.org/bots#creating-a-new-bot)
- [heroku](https://heroku.com)
- [redis](https://redislabs.com/)
- [elasticpath](https://www.elasticpath.com/)

### Project Goals

The code is written for educational purposes on online-course for web-developers [dvmn.org](https://dvmn.org/).
