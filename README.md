# Jumper-Cogs
Python Modules for Discord bot

Developer: Redjumpman

####*Lottery*
- Enables admins to start a lottery
- Only members who have signed up can play in a lottery
- Requires you to be online and type !lottery play to participate in an on-going lottery
- Ending a lottery will declare a winner, randomly picked from participating members
- Members can check how many lotteries they have participated in and won

#####*Note* This cog will create a data folder named "lottery" which contains three JSON files:
- players - contains all the members who signed up and uses this to determine winners
- system - determines if a lottery is active and records the number of lotteries ran
- lottery - Creates a log for errors with the lottery.

####*Pokedex*
- Search for pokemon catch locations
- Search for items
- Retrieve base stats along with their min/max at Lvl. 100
- Pokedex information
- Evolution chains
- Moveset lookup (By generations!)

####*Fortune*
Simple extension that will display a fortune. Can add your own in the file.

####*Dicetable*
Allows the user to roll up to 20 dice and outputs the data into a table. Includes the following variants:
- d20
- d12
- d10
- d8
- d6
- d4

Perfect for roleplaying games like DnD and Pathfinder!

####*Shop*
- Admins can create items and set prices
- Users can purchase these items
- Items are giftable to other players
- Items can be "redeemed" by sending them to a pending list
- Admins can approve and clear the pending list
- Can check items in your inventory, type !inventory
- Uses Economy.py system points  

Perfect for integrating with other games on your discord server!  
Check my wiki for further documentation

####*Tibia*
- Retrieves creature information
- Retrieves item information
- Shows total players playing Tibia
- Shows server information
- Will tell you where Rashid is located for the day


# Installation

####*Cog Install*

cog install Jumper-Cogs "cogname"

*OR*

download the .py file and place it in your cog folder.

####*Dependencies*
Some of my cogs will require you download a library.

To install a library follow these instructions:
```
- Open command prompt
- Type pip3 install "Library name"   Example: pip3 install tabulate
- Press enter and let the library load
- Once this has loaded you just need to install the cog!
```
####*Pokedex cog* 
Library Requirements:
- Tabulate
- BeautifulSoup4

####*Dicetable*
Library Requirements:
- Tabulate

####*Tibia*
Library Requirements:
- Tabulate
- BeautifulSoup4

####*Shop*
Library Requirements:
- Tabulate

# What's planned?

- League of Legends
- WoW Armory
- Raid Calendar (With support to sync your own)
- Spotify (Will require you to have your own account)
- DnD (will include spell lookups, magic item generator, and lore search)
- I have a lot of ideas and will constantly update this list based on requests!

# Suggestions
Have an idea for a cog? Start an issue on this repository and I will try to work on it.

