# Captains: Set Season Group (for a team)

Once teams are configured for the season, the team captains (captain role not required) can set up a ballchasing group for their current season.

Note: **ONLY** the top level group is required, (i.e. RSC S15 Gorillas)

<br>

## Contents
- [**Contents** (here!)](#contents)
- [**Overview**](#overview)
    - [Administrative Prerequisites](#gmserver-owner-prerequisites)
    - [Player Prerequisites](#player-prerequisites)
- [**Full Instructions**](#full-instructions) (Good Place to start)
    - [Register your Ballchasing Token](#1-register-your-ballchasing-token-with-the-bot)
    - [Register a Steam Account](#2-register-your-steam-account-with-the-bot)
        - [How can I find my platform id?](#how-can-i-find-my-steam-platform-id)
        - [Account Registration](#account-registration)
    - [Register Your Team's Ballchasing Season Group](#3-set-your-top-level-group-for-the-season)
        - [Create Ballchasing Group](#1-create-ballchasing-group) (returning players can start here)
        - [Get the new group link/code](#2-get-the-link-or-group-id-from-your-new-group)
        - [Register the group with the bot](#3-register-the-team-ballchasing-group-for-the-season)


<br>

# Overview

## GM/Server Owner Prerequisites
- Must have `accountManager` cog set up (**Note:** bot owner action)
- Must register a ballchasing upload token with the bot (`<p>help setGuildBCAuthToken`)
- Must register team roles with the bot (`<p>help setFranchiseTeams`, `<p>help clearFranchiseTeams`)
- At the end of a season, user `<p>endSeason` to clear all set team groups to prevent new subgroups being added to the previous season's group

## Player Prerequisites
- Must have a steam account registered with the bot (`<p>help registerAccount`)
- Must register your ballchasing upload token with the bot (`<p>setMyBCAuthToken`)
- Must upload ballchasing replays to this account

## Information Checks
- `<p>tokenCheck` checks if you have registered a valid ballchasing token
- `<p>getSeasonGroup` returns the top level ballchasing group for your team role

<br>

# Full Instructions

## 1. Register your ballchasing token with the bot.

Your token can be retrieved by signing into ballchasing.com with your steam account, and going to the uploads tab (top center), or by going to it directly by its url at https://ballchasing.com/upload.

![](https://media.discordapp.net/attachments/741758967260250213/1019695110826504242/unknown.png?width=2251&height=553)

- If you've generated a token before, click on the paper icon to the left of "Show."
- If you have not, click on the yellow refresh button to generate a new token.

When you have copied the token, you'll want to register it with the bot.

```
<p>setMyBCAuthToken <YOUR TOKEN>
```

## 2. Register your steam account with the bot.
You must register the same account you used to sign in and register an upload token. For the bot to work best, it is **strongly** encouraged to [enable automatic uploads](https://ballchasing.com/doc/faq#upload) with **BakkesMod**. 

Note: You can not use your display name to register your account. This will not work!

<br>

#### **How can I find my steam platform ID?**

1. **Use ballchasing.com!** (Works for all platforms)

    a. Navigate to your player page by signing in and clicking on your profile at the top right (**Note:** Don't click log out, just click on your name.)

    ![](https://media.discordapp.net/attachments/741758967260250213/1019711228999893043/unknown.png?width=2251&height=358)

    **OR**
    
    b. Find an uploaded replay where you played, and click on your name.

    ![](https://cdn.discordapp.com/attachments/741758967260250213/1019710941216129144/unknown.png)
    
    Either of these actions will take you to your player page, where you can find your platform id in the url of that page.

    ![](https://media.discordapp.net/attachments/741758967260250213/1019713823101435965/unknown.png?width=2251&height=581)

    The platform and platform ID can be found in the url of any account page. The url for every account page ends in the format of `/platform/platform_id`.
    
    In this example, the URL is `https://ballchasing.com/player/steam/76561198380344413`.

    That means that
    - The `platform` is `steam`
    
      and

    - The `platform_id` is `76561198380344413`.

1. **Look it up on Tracker Network** (similar solution as above)
1. **Use a Steam ID lookup service**

    - [STEAMID IO](https://steamid.io/) is a good tool to use for this.

      You can look up any of your steam accounts with this tool. In this case, the `platform_id` is `steamID64`:

      ![](https://cdn.discordapp.com/attachments/741758967260250213/1019715204222832701/unknown.png)


#### **Account Registration**

Registering a new account with the bot must be done in the following format:
      
    <p>registerAccount <platform> <platform_id>

Example Registration:

    <p>registerAccount steam 76561198380344413

**Note:** If other players on your team will be uploading replays to ballchasing, encourage them to register their accounts as well. Your teammates may, but are not required to register an upload token.

## 3. Set your Top Level Group for the season

Once the pre-requisite steps (1-2) are done, group registration is very easy! All you need to do is create a ballchasing group for your team on the current season, and use `<p>setSeasonGroup` to save it to the bot.

<br>

#### **1. Create ballchasing group**

1. Under `Replay Groups` click on `My replay Groups`
![](https://cdn.discordapp.com/attachments/741758967260250213/1019698623174422628/unknown.png)

1. **Create a New Ballchasing Group**

    - **[Option 1]** Scroll down and click `Create New Group`
      
      ![](https://cdn.discordapp.com/attachments/741758967260250213/1019699256958918708/unknown.png)

    - **[Option 2]** If you want your ballchasing group to be in another subgroup, you may navigate to that point and make the subgroup there by clicking `New Group`.
    
        ![](https://media.discordapp.net/attachments/741758967260250213/1019700329207574729/unknown.png)

1. Give your group a name, and set the configurations to align with the screenshot below:

    ![](https://cdn.discordapp.com/attachments/741758967260250213/1019699889791316118/unknown.png)

<br>

#### **2. Get the link or group ID from your new group.**

1. Navigate to your new season ballchasing group

    ![](https://cdn.discordapp.com/attachments/741758967260250213/1019701372314198067/unknown.png)

    In this example, you can see the url is `https://ballchasing.com/group/s15-gorillas-oj7jeak7kq`. The ballchasing group code is everything that follows `group/`. So in this example, the group code is `s15-gorillas-oj7jeak7kq`. Either value can be used when using the following command to set the season group.

<br>

#### **3. Register the Team Ballchasing Group for the season**

As stated previously, either the link or the group code can be used to register the season group

- Link: `https://ballchasing.com/group/s15-gorillas-oj7jeak7kq`
- Group: `s15-gorillas-oj7jeak7kq`

Use `<p>setSeasonGroup <link or code>` to register your group

```
<p>setSeasonGroup https://ballchasing.com/group/s15-gorillas-oj7jeak7kq
```
OR
```
<p>setSeasonGroup s15-gorillas-oj7jeak7kq
```

<br>

## That's it! You should be all set now! If you have any further questions, please ask your GM or contact nullidea#3117 on discord.

