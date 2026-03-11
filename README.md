# myGoogleCalendar

You can authenticate by using the 2FA authenticator code

A simple program to copy my shifts from Target myTime to Google Calendar. 

Hello all! I am using the Google Calendar API for this. If you would like to use this code. You MUST be a Google Cloud developer (its free) and get a Google Auth Key. 

# How does this work?

This code will authenticate you, save your token, and call the WFM API which allows this script to be ran multiple times whilst keeping the same token.

To ensure your shifts are always the most recent onces, on every run it is going to verify any previous shifts added and change them if needed. This makes sure that if a time or a workcentre changes, You're still good to go. 


# **Lets Get Started!**. 

First you need to clone this project. Do this however you'd like.
Once you've done that, all the working file are going to be in the V2 folder. I wrote V1 when I was new to coding and it is written very very badly. 
V2 is significantly more efficient . 

# **Google API Key**
First you need a form of authenticating with Google Calendar

Goto [console.cloud.google.com](https://console.cloud.google.com/)

https://youtu.be/c2b2yUNWFzI?t=225 this is a great video explaining the setting up the OAuth for Google Calendar. Watch till 10:05 minutes and come back to this documnentation 

Welcome back!

Quick Thing, While you're in the cloud console, Goto API & Services, OAuth Consent Screen, and switch your app from "Testing" to "Production"
![image](https://github.com/user-attachments/assets/0d396f76-20e1-491e-8cab-8d58e555c8cb)
Testing tokens last a week while Production Tokens last alot longer ( I think permenant? Hard to say, many conflicting answers online ) 

Once you create your OAuth, click download JSON on the right side. 
Drop it into the main directory of your working directory.

Rename the file **"credentials.json"**

# **Setting up your config file** 
Now, goto the **config_template.py** file in the main directory and change the info in there to match your information. Lets break down what all of these do. 


# Global Variables
```EMPLOYEE_ID = 00000000```
Replace these numbers with your TMID you use at the time clock

```PASSWORD = "myPassword"``` 
Replace password with your password when you sign into Workday or Target Pay and Benefits. 

```STORE_NUMBER = 1375```
Replace this with  your 4 digit store number is. 
Note if your store number is less than 4 digits, like store number 192, make sure you have a leading 0, so in this case it would be 0192

```API_KEY = "eb2551e4accc14f38cc42d32fbc2b2ea"```
You can change this but the default one should work

```
PUSHOVER_APP_API_KEY = ""
PUSHOVER_USER_API_KEY = ""
```
These two lines are if you want to get notifications on your phone about any posted shifts AND if you want to get notified that a shift was added to your Google calendar. 
If you don't want to get these notifications, just leave these two strings empty

If you don't want this script to scan for posted shifts
```run_posted_shifts = True``` 
If this is set to true, then it will read the available shifts in your store and notify you via Pushover. You need to setup the pushover APP and USER API key in the above block though. 
```headless = True``` 
Headless means that you wont see see Chrome open to obtain the Bearer.
# The Hardest Part

# ** READ ALL THE STEPS IN THIS SECTION! **

This is the hardest part about the entire setup process about this. As your form of multifactor authentication you need to obtain a One Time Password code. 
***You need to be on the Target Internal Network for this part of the setup.***
Once you're at work, log into **https://mylogin.prod.target.com** and there should be a section of setting up an Authenticator App.
Note: I used a ChromeBox but you should be able to use a myDevice

You can use any kind of regular authenticator app like Authy, 1Password, Okta Verify, Google Authenticator, Etc. 
(Side note, Target SSO now has 1Password Passkey support so I personally reccomend using 1Password as your primary Password Manager if you haven't already)
If you don't wanna pay for 1Password you can use anything else in that list. I personally reccomend Authy since it allows you to backup and encrypt your MFA codes. 
***BEFORE YOU COMPLETE THE ENROLLMENT TAKE A PICTURE OF THE QR CODE!!!!***
Now complete the enrollment.

Now lets get back to the enrollment. If you convert the QR code to plaintext, it should look something like this ```otpauth://totp/?1234567secret=REALLYLONGTOKEN&issuer=Target%20SSO``` 
Now we can put this token into our script. 
```totp = pyotp.TOTP("")```
In the example, we're going to take the part of the URL that says ```REALLYLONGTOKEN``` and put it into the quotes. 
It should look like this ```totp = pyotp.TOTP("REALLYLONGTOKEN")```

Finally rename ```config_template.py``` to ```config_file.py```

# 1Password Integration (Optional)

Instead of storing your credentials directly in `config_file.py`, you can pull them from 1Password automatically using the official Python SDK.

## Setup

1. **Create a Service Account** in 1Password:
   - Go to [1password.com](https://1password.com) > Developer Tools > Service Accounts
   - Create a new service account
   - Grant it access to **only** the vault containing your Target login
   - Copy the service account token (it's only shown once)

2. **Install the SDK**:
   ```bash
   pip install onepassword-sdk
   ```

3. **Configure `config_file.py`**:
   ```python
   USE_1PASSWORD = True
   OP_SERVICE_ACCOUNT_TOKEN = "your-service-account-token"
   OP_EMPLOYEE_ID_REF = "op://YourVault/YourItem/username"
   OP_PASSWORD_REF = "op://YourVault/YourItem/password"
   OP_TOTP_SECRET_REF = "op://YourVault/YourItem/one-time password"
   ```

## Finding Your Secret References

The format is `op://Vault/Item/Field` where:
- **Vault** is the name of the vault (e.g., "Personal", "Automation")
- **Item** is the name of the login entry (whatever you titled it)
- **Field** is the field label — open the item in 1Password and check what each field is called. Common defaults are `username`, `password`, and `one-time password`

## Security Tip

Create a dedicated vault (e.g., "Automation") with only the Target login in it, then grant the service account access to just that vault. This way the service account can't access anything else in your 1Password account.

# Lets start!
Now that everything is setup. run ```pip install -r requirements.txt``` and it will install all the requirements needed!
Give it a shot and run the code by running ```python top.py```. 

# Did it error out? 
If it fails. Try to add chromedriver to your OS path.
For some reason, some users are having issues with SQLAlchemy, if the code is complaining about SQLAlchemy, ```pip install SQLAlchemy``` in your environment. Should work  

# Why is it asking for my Google?

You should see something along the lines of this. 
![image](https://github.com/user-attachments/assets/25518b7d-d259-47cb-8b08-6347f48330f2)
Its basically asking you which account you want to link to the script to push calendar events to 

# IS THIS A WIRUS?
If you have not verified your application (which is not required, theres no real reason to verify in our case), you will see a message like this. 
![image](https://github.com/user-attachments/assets/b54666f8-5209-4c61-8d9a-92295da0fe80)

All this is saying is that the application that you made has not been verified. Google this is more if you'd want to make something like this a public thing, like good integration in your app. You're more than welcome to verify it thru google but you're wasting your time. Hit show advanced and then hit ```Go to [whatever you named your Cloud Project] (unsafe)```. 

All this code is open source, if you don't feel comfortable with hitting that button, you can go through this code line by line to ensure that it is safe. 

And you're done!

In theory your Google Calendar is getting filled with your target shifts!


# Having issues?
If you're having issues feel free to shoot me a message on discord ```versiondefect``` or just make a issue / open a new discussion post. 
Happy planning!
