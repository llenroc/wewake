
0. Download SQLite3. Set up the db file, by running `sqlite3 db`. Quit SQLite, then run `sqlite3 db < db_setup.sql` in the shell to set up the empty tables.
1. Set up a Twilio account. Find your phone number, account SID and auth token.
2. Edit config.py. Fill in the details from above. Set app_url to be the public URL for your server. Make sure your Twilio account also uses the same app_url for the messaging endpoint.
3. (Optional) To host locally and tunnel, download ngrok and use the following command: `ngrok --subdomain=<whateveryouwant> 5000`
4. Run `python wewake.py`. The server will run on port 5000.