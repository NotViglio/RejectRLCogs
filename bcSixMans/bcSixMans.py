import abc
from .config import config
import requests
from datetime import datetime, timezone
import tempfile
import discord
import asyncio
import urllib.parse

from redbot.core import Config
from redbot.core import commands
from redbot.core import checks
from redbot.core.utils.predicates import ReactionPredicate
from redbot.core.utils.menus import start_adding_reactions

defaults =   {"AuthToken": None, "TopLevelGroup": None, "AccountRegister": {}}
verify_timeout = 30

class BCSixMans(commands.Cog):
    """Manages aspects of Ballchasing Integrations with RSC"""

    def __init__(self, bot):
        self.bot = bot
        self.config = Config.get_conf(self, identifier=1234567893, force_registration=True)
        self.config.register_guild(**defaults)
        self.six_mans_cog = bot.get_cog("SixMans")
        # TODO: self.token = await self._auth_token # load on_ready

    # TODO: automatically run when score reported -- allow to  coexist with the auto-replay-uploader
    @commands.command(aliases=['ggs', 'gg'])
    @commands.guild_only()
    async def gameOver(self, ctx): # , games_played:int):
        """Finds replays from the six mans series based on the number of games played, and links a new ballchasing group for the series.
        """
        # Find Six Mans Game, Queue
        member = ctx.message.author
        self.six_mans_cog = self.bot.get_cog("SixMans")
        game = None
        for g in self.six_mans_cog.games:
            if g.textChannel == ctx.message.channel:
                game = g
                break
        

        if not len(self.six_mans_cog.games):
            return
            # await game_text_channel.send("no ongoing games")

        if not game:
            await ctx.send("game not found.")
            return False

        await self._process_six_mans_replays(ctx.guild, game)

    @commands.command(aliases=['setBCAuthKey'])
    @commands.guild_only()
    @checks.admin_or_permissions(manage_guild=True)
    async def setBCAuthToken(self, ctx, auth_token):
        """Sets the Auth Key for Ballchasing API requests.
        Note: Auth Token must be generated from the Ballchasing group owner
        """
        token_set = await self._save_auth_token(ctx, auth_token)
        if(token_set):
            await ctx.send("Done.")
        else:
            await ctx.send(":x: Error setting auth token.")

    @commands.command(aliases=["sbcg", "setTopLevelGroup"])
    @commands.guild_only()
    @checks.admin_or_permissions(manage_guild=True)
    async def setBCGroup(self, ctx, top_level_group_id):
        """Sets the Top Level Ballchasing Replay group for saving match replays.
        Note: Auth Token must be generated from the Ballchasing group owner
        """
        # TODO: validate group
        top_level_group_id = top_level_group_id.replace('https://', '').replace('ballchasing.com/group/', '')
        group_set = await self._save_top_level_group(ctx, top_level_group)
        if(group_set):
            await ctx.send("Done.")
        else:
            await ctx.send(":x: Error setting top level group.")
    
    @commands.command(aliases=['bcGroup', 'ballchasingGroup', 'bcg', 'getBCGroup'])
    @commands.guild_only()
    async def bcgroup(self, ctx):
        """Get the top-level ballchasing group to see all season match replays."""
        group_code = await self._get_top_level_group(ctx.guild)
        url = "https://ballchasing.com/group/{}".format(group_code)
        await ctx.send("See all season replays in the top level ballchasing group: {}".format(url))

    @commands.command(aliases=['bcpage', 'mybc', 'bcp', 'getBCPage', 'bcprofile', 'bcpages'])
    @commands.guild_only()
    async def bcProfile(self, ctx, member:discord.Member=None):
        """Get the ballchasing pages for registered accounts"""
        group_code = await self._get_top_level_group(ctx.guild)
        if not member:
            member = ctx.message.author
        lines = []
        for acc in await self._get_all_accounts(ctx.guild, member):
            lines.append("<https://ballchasing.com/player/{}/{}>".format(acc[0], acc[1]))
        show_accounts = "**{}**, has registered the following accounts:\n - ".format(member.name) + "\n - ".join(lines)
        await ctx.send(show_accounts)

    @commands.command(aliases=['registeraccount', 'accountregister', 'accountRegister', 'addAccount', 'addaccount', 'addacc'])
    @commands.guild_only()
    async def registerAccount(self, ctx, platform:str, identifier:str):
        """Allows user to register account for ballchasing requests. This may be found by searching your appearances on ballchasing.com

        Examples:
            [p]registerAccount steam 76561199096013422
            [p]registerAccount xbox e4b17b0000000900
            [p]registerAccount ps4 touchetupac2
            [p]registerAccount epic 76edd61bd58841028a8ee27373ae307a
            [p]registerAccount steam
        """
        # Check platform
        platform = platform.lower()
        if platform not in ['steam', 'xbox', 'ps4', 'ps5', 'epic']:
            await ctx.send(":x: \"{}\" is an invalid platform".format(platform))
            return False
        

        member = ctx.message.author
        # Profile can't be seen from bots :/
        # if not identifier:
        #     return 
        #     if platform.lower() in ['ps4', 'ps5']:
        #         await ctx.send(":x: Discord does not support linking to **{}** accounts. Auto-detection failed.".format(platform))
        #         return False

        #     identifier = await self._auto_link_account(member, platform)

        # Validate account -- check for public ballchasing appearances
        valid_account = await self._validate_account(ctx, platform, identifier)

        if valid_account:
            username, appearances = valid_account
        else:
            await ctx.send(":x: No ballchasing replays found for user: {identifier} ({platform}) ".format(identifier=identifier, platform=platform))
            return False

        account_register = await self._get_account_register(ctx.guild)
        
        # Make sure not a repeat account
        if str(member.id) in account_register and [platform, identifier] in account_register[str(member.id)]:
            await ctx.send("{}, you have already registered this account.".format(member.mention))
            return False

        # React to confirm account registration
        prompt = "**{username}** ({platform}) appears in **{count}** ballchasing replays.".format(username=username, platform=platform, count=appearances)
        prompt += "\n\nWould you like to register this account?"
        nvm_message = "Registration cancelled."
        if not await self._react_prompt(ctx, prompt, nvm_message):
            return False
            
        if str(member.id) in account_register:
            account_register[str(member.id)].append([platform, identifier])
        else:
            account_register[str(member.id)] = [[platform, identifier]]
        
        # Register account
        if await self._save_account_register(ctx.guild, account_register):
            await ctx.send("Done")

    @commands.command(aliases=['rmaccount', 'removeAccount'])
    @commands.guild_only()
    async def unregisterAccount(self, ctx, platform, identifier=None):
        remove_accs = []
        account_register = await self._get_account_register(ctx.guild)
        member = ctx.message.author
        if str(member.id) in account_register:
            for account in account_register[str(member.id)]:
                if account[0] == platform:
                    if not identifier or account[1] == identifier:
                        remove_accs.append(account)
        
        if not remove_accs:
            await ctx.send(":x: No matching account has been found.")
            return False
        
        prompt = "React to confirm removal of the following account(s):\n - " + "\n - ".join("{}: {}".format(acc[0], acc[1]) for acc in remove_accs)
        if not await self._react_prompt(ctx, prompt, "No accounts have been removed."):
            return False
        
        count = 0
        for acc in remove_accs:
            account_register[str(member.id)].remove(acc)
            count += 1
        
        await self._save_account_register(ctx.guild, account_register)
        await ctx.send(":white_check_mark: Removed **{}** account(s).".format(count))

    @commands.command(aliases=['rmaccounts', 'clearaccounts', 'clearAccounts'])
    @commands.guild_only()
    async def unregisterAccounts(self, ctx):
        """Unlinks registered account for ballchasing requests."""
        account_register = await self._get_account_register(ctx.guild)
        discord_id = str(ctx.message.author.id)
        if discord_id in account_register:
            count = len(account_register[discord_id])
            accounts = await self._get_all_accounts(ctx, ctx.message.author)
            prompt = "React to confirm removal of the following accounts ({}):\n - ".format(len(accounts)) + "\n - ".join("{}: {}".format(acc[0], acc[1]) for acc in accounts)
            if not await self._react_prompt(ctx, prompt, "No accounts have been removed."):
                return False
            
            del account_register[discord_id]
            await ctx.send(":white_check_mark: Removed **{}** account(s).".format(count))
        else:
            await ctx.send("No account found.")

    @commands.command(aliases=['accs', 'myAccounts', 'registeredAccounts'])
    @commands.guild_only()
    async def accounts(self, ctx):
        """view all accounts that have been registered to with your discord account in this guild."""
        member = ctx.message.author
        accounts = await self._get_all_accounts(ctx, member)
        if not accounts:
            await ctx.send("{}, you have not registered any accounts.".format(member.mention))
            return

        show_accounts = "{}, you have registered the following accounts:\n - ".format(member.mention) + "\n - ".join("{}: {}".format(acc[0], acc[1]) for acc in accounts)
        await ctx.send(show_accounts)

    @commands.command(aliases=['getAccounts', 'getRegisteredAccounts', 'getAccountsRegistered', 'viewAccounts', 'showAccounts'])
    @commands.guild_only()
    @checks.admin_or_permissions(manage_guild=True)
    async def memberAccounts(self, ctx, *, member: discord.Member):
        """view all accounts that have been registered to with your discord account in this guild."""
        accounts = await self._get_all_accounts(ctx.guild, member)
        if not accounts:
            await ctx.send("**{}**, has not registered any accounts.".format(member.name))
            return

        show_accounts = "**{}**, has registered the following accounts:\n - ".format(member.name) + "\n - ".join("{}: {}".format(acc[0], acc[1]) for acc in accounts)
        await ctx.send(show_accounts)

    @commands.command(aliases=['allaccs', 'allaccounts'])
    @commands.guild_only()
    @checks.admin_or_permissions(manage_guild=True)
    async def getAllAccounts(self, ctx):
        """lists all accounts registered for troubleshooting purposes"""
        account_register = await self._get_account_register(ctx.guild)
        if not account_register:
            return await ctx.send("No accounts have been registered.")
        output = "All Accounts:\n"
        member_lines = "discord id:         platform - id"
        for member, accs in account_register.items():
            for acc in accs:
                member_lines += "\n{}: {} - {}".format(member, acc[0], acc[1])
                if len(member_lines) > 1800:
                    await ctx.send(output + "\n```{}```".format(member_lines))
                    output = ""
                    members = ""
        await ctx.send(output + "```\n{}\n```".format(member_lines))

    @commands.command(aliases=['gsids'])
    @commands.guild_only()
    @checks.admin_or_permissions(manage_guild=True)
    async def getSteamIds(self, ctx):
        steam_ids = await self._get_steam_ids(ctx, ctx.message.author.id)
        for sid in steam_ids:
            await ctx.send(sid)

    @commands.command(aliases=['cw'])
    @commands.guild_only()
    @checks.admin_or_permissions(manage_guild=True)
    async def whenCreated(self, ctx):
        created = ctx.channel.created_at.astimezone(tz=timezone.utc).isoformat()
        await ctx.send("Channel created: {}".format(created))

    @commands.command()
    @commands.guild_only()
    @checks.admin_or_permissions(manage_guild=True)
    async def observe(self, ctx):
        if True:
        # if self.observe_six_mans():
            await ctx.send("Observing!")

    @commands.guild_only()
    @commands.Cog.listener("on_ready")
    async def on_ready(self):
        self.observe_six_mans()

    @commands.guild_only()
    @commands.Cog.listener("on_resumed")
    async def on_resumed(self):
        self.observe_six_mans()

    def observe_six_mans(self):
        self.six_mans_cog = self.bot.get_cog("SixMans")
        if not self.six_mans_cog.is_observing(self):
            self.six_mans_cog.add_observer(self)
            return True
        return False


    async def update(self, game):
        if game.game_state == "game over":
            await game.textChannel.send("Hey! The game is over kek")


    # TODO: there's a lot to change. just go by one method at a time and replace ctx with parameters of what it needs. good luck king.
    async def _process_six_mans_replays(self, guild, game):

        six_mans_queue = None
        for q in self.six_mans_cog.queues:
            if game.queueId == q.id:
                six_mans_queue = q
                break
        
        if not six_mans_queue:
            await game.textChannel.send("queue not found.")
            return False

        if not await self._get_top_level_group(guild):
            await game.textChannel.send('ballchasing group group not found.')
            return False

        # Start Ballchasing Process:
        await game.textChannel.send("_Finding ballchasing replays..._")

        # Find Series replays
        replays_found = await self._find_series_replays(guild, game) 

        # here
        if not replays_found:
            await game.textChannel.send(":x: No matching replays found.")
            return False

        series_subgroup_id = await self._get_replay_destination(guild, six_mans_queue, game)
        # await text_channel.send("Match Subgroup ID: {}".format(series_subgroup_id))
        if not series_subgroup_id:
            return await game.textChannel.send(":x: series_subgroup_id not found.")

        replay_ids, summary = replays_found
        # await text_channel.send("Matching Ballchasing Replay IDs ({}): {}".format(len(replay_ids), ", ".join(replay_ids)))
        
        try:
            await game.textChannel.send("_Processing {} replays..._".format(len(replay_ids)))
        except:
            pass
        tmp_replay_files = await self._download_replays(guild, replay_ids)
        # await text_channel.send("Temp replay files to upload ({}): {}".format(len(tmp_replay_files), ", ".join(tmp_replay_files)))
        
        uploaded_ids = await self._upload_replays(guild, series_subgroup_id, tmp_replay_files)
        # await text_channel.send("replays in subgroup: {}".format(", ".join(uploaded_ids)))
        
        renamed = await self._rename_replays(guild, uploaded_ids)
        # await text_channel.send("replays renamed: {}".format(renamed))
        
        try:
            message = ':white_check_mark: {}\n\nReplays added to ballchasing subgroup ({}): <https://ballchasing.com/group/{}>'.format(summary, len(uploaded_ids), series_subgroup_id)
            await game.textChannel.send(message)
        except:
            pass

    # good
    async def _get_all_accounts(self, guild, member):
        accs = []
        account_register = await self._get_account_register(guild)
        discord_id = str(member.id)
        if discord_id in account_register:
            for account in account_register[discord_id]:
                accs.append(account)
        return accs

    # good
    async def _bc_get_request(self, guild, endpoint, params=[], auth_token=None):
        if not auth_token:
            auth_token = await self._get_auth_token(guild)
        
        url = 'https://ballchasing.com/api'
        url += endpoint
        # params = [urllib.parse.quote(p) for p in params]
        params = '&'.join(params)
        if params:
            url += "?{}".format(params)
        
        # url = urllib.parse.quote_plus(url)
        
        return requests.get(url, headers={'Authorization': auth_token})

    # good
    async def _bc_post_request(self, guild, endpoint, params=[], auth_token=None, json=None, data=None, files=None):
        if not auth_token:
            auth_token = await self._get_auth_token(guild)
        
        url = 'https://ballchasing.com/api'
        url += endpoint
        params = '&'.join(params)
        if params:
            url += "?{}".format(params)
        
        return requests.post(url, headers={'Authorization': auth_token}, json=json, data=data, files=files)

    # good
    async def _bc_patch_request(self, guild, endpoint, params=[], auth_token=None, json=None, data=None):
        if not auth_token:
            auth_token = await self._get_auth_token(guild)

        url = 'https://ballchasing.com/api'
        url += endpoint
        params = '&'.join(params)
        if params:
            url += "?{}".format(params)
        
        return requests.patch(url, headers={'Authorization': auth_token}, json=json, data=data)

    # leave
    async def _react_prompt(self, ctx, prompt, if_not_msg=None):
        user = ctx.message.author
        react_msg = await channel.send(prompt)
        start_adding_reactions(react_msg, ReactionPredicate.YES_OR_NO_EMOJIS)
        try:
            pred = ReactionPredicate.yes_or_no(react_msg, user)
            await ctx.bot.wait_for("reaction_add", check=pred, timeout=verify_timeout)
            if pred.result:
                return True
            if if_not_msg:
                await ctx.send(if_not_msg)
            return False
        except asyncio.TimeoutError:
            await ctx.send("Sorry {}, you didn't react quick enough. Please try again.".format(user.mention))
            return False

    # good
    async def _validate_account(self, ctx, platform, identifier):
        # auth_token = config.auth_token
        auth_token = await self._get_auth_token(ctx.guild)
        endpoint = '/replays'
        params = [
            'player-id={platform}:{identifier}'.format(platform=platform, identifier=identifier),
            'count=1'
        ]
        r = await self._bc_get_request(ctx.guild, endpoint, params)
        data = r.json()

        appearances = 0
        username = None
        if data['list']:
            for team_color in ['blue', 'orange']:
                for player in data['list'][0][team_color]['players']:
                    if player['id']['platform'] == platform and player['id']['id'] == identifier:
                        username = player['name']
                        appearances = data['count']
                        break
        if username:
            return username, appearances
        return False

    # good
    async def _get_steam_id_from_token(self, guild, auth_token=None):
        if not auth_token:
            auth_token = await self._get_auth_token(guild)
        r = await self._bc_get_request(guild, "")
        if r.status_code == 200:
            return r.json()['steam_id']
        return None

    # good
    async def _get_steam_ids(self, guild, discord_id):
        discord_id = str(discord_id)
        steam_accounts = []
        account_register = await self._get_account_register(guild)
        if discord_id in account_register:
            for account in account_register[discord_id]:
                if account[0] == 'steam':
                    steam_accounts.append(account[1])
        return steam_accounts

    def _is_full_replay(self, replay_data):
        if replay_data['duration'] < 300:
            return False

        orange_goals = replay_data['orange']['goals'] if 'goals' in replay_data['orange'] else 0
        blue_goals = replay_data['blue']['goals'] if 'goals' in replay_data['blue'] else 0

        if orange_goals == blue_goals:
            return False
        for team in ['blue', 'orange']:
            for player in replay_data[team]['players']:
                if player['start_time'] == 0:
                    return True
        return False

    def _get_account_replay_team(self, platform, plat_id, replay_data):
        for team in ['blue', 'orange']:
            for player in replay_data[team]['players']:
                if player['id']['platform'] == platform and player['id']['id'] == str(plat_id):
                    return team
        return None

    # good
    async def _is_six_mans_replay(self, guild, uploader, sm_game, replay_data, use_account=None):
        """searches for the uploader's appearance in the replay under any registered account"""
        if use_account:
            account_register = {uploader.id: [account]}
        else:
            account_register = await self._get_account_register(guild)
        
        # which team is the uploader supposed to be on
        if uploader in sm_game.blue:
            uploader_sm_team = 'blue'
        elif uploader in sm_game.orange:
            uploader_sm_team = 'orange'
        else:
            return None

        # swap_teams covers the scenario where the teams join incorrectly, assumes group is correct (applies to score summary only)
        swap_teams = False
        for account in account_register[str(uploader.id)]:
            platform, plat_id = account
            
            # error here
            account_replay_team = self._get_account_replay_team(platform, plat_id, replay_data)
            await sm_game.textChannel.send("uploader team: {}\naccount team: {}".format(uploader_sm_team))

            if account_replay_team and uploader_sm_team != account_replay_team:
                swap_teams = True

        # don't count incomplete replays
        if not self._is_full_replay(replay_data):
            return False

        # determine winner
        orange_goals = replay_data['orange']['goals'] if 'goals' in replay_data['orange'] else 0
        blue_goals = replay_data['blue']['goals'] if 'goals' in replay_data['blue'] else 0
        if blue_goals > orange_goals:
            winner = 'blue'
        else:
            winner = 'orange'
        
        # swap teams if necessary
        if swap_teams and False:
            await sm_game.textChannel.send("swapped teams")
            if winner == 'orange':
                winner = 'blue'
            elif winner == 'blue':
                winner = 'orange'

        return winner

    # good
    async def _get_replay_destination(self, guild, queue, game):
        
        auth_token = await self._get_auth_token(guild)
        bc_group_owner = await self._get_steam_id_from_token(guild, auth_token)
        top_level_group = await self._get_top_level_group(guild)

        # /<top level group>/<queue name>/<game id>
        game_id = game.id
        blue_players = game.blue 
        oran_players = game.orange
        queue_name = queue.name # next(queue.name for queue in self.queues if queue.id == six_mans_queue.id)

        ordered_subgroups = [
            queue_name,
            game_id
        ]

        endpoint = '/groups'
        
        params = [
            # 'player-id={}'.format(bcc_acc_rsc),
            'creator={}'.format(bc_group_owner),
            'group={}'.format(top_level_group)
        ]

        r = await self._bc_get_request(guild, endpoint, params, auth_token)
        data = r.json()

        # Dynamically create sub-group
        current_subgroup_id = top_level_group
        next_subgroup_id = None
        for next_group_name in ordered_subgroups:
            next_group_name = str(next_group_name)
            if next_subgroup_id:
                current_subgroup_id = next_subgroup_id
            next_subgroup_id = None 

            # Check if next subgroup exists
            if 'list' in data:
                for data_subgroup in data['list']:
                    if data_subgroup['name'] == next_group_name:
                        next_subgroup_id = data_subgroup['id']
                        break
            
            # Prepare & Execute  Next request:
            # ## Next subgroup found: request its contents
            if next_subgroup_id:
                params = [
                    'creator={}'.format(bc_group_owner),
                    'group={}'.format(next_subgroup_id)
                ]

                r = await self._bc_get_request(ctx, endpoint, params, auth_token)
                data = r.json()

            # ## Creating next sub-group
            else:
                payload = {
                    'name': next_group_name,
                    'parent': current_subgroup_id,
                    'player_identification': config.player_identification,
                    'team_identification': config.team_identification
                }
                r = await self._bc_post_request(guild, endpoint, auth_token=auth_token, json=payload)
                data = r.json()
                
                if 'error' not in data:
                    try:
                        next_subgroup_id = data['id']
                    except:
                        return False
            
        return next_subgroup_id

    # good
    async def _find_series_replays(self, guild, game):
        # search for appearances in private matches
        endpoint = "/replays"
        sort = 'replay-date'
        sort_dir = 'desc'
        count = 7
        # queue_pop_time = ctx.channel.created_at.isoformat() + "-00:00"
        queue_pop_time = game.textChannel.created_at.astimezone(tz=timezone.utc).isoformat()
        auth_token = await self._get_auth_token(guild)
        
        params = [
            'playlist=private',
            'replay-date-after={}'.format(urllib.parse.quote(queue_pop_time)),
            'count={}'.format(count),
            'sort-by={}'.format(sort),
            'sort-dir={}'.format(sort_dir)
        ]
        
        for player in game.players:
            for steam_id in await self._get_steam_ids(guild, player.id):
                uploaded_by_param='uploader={}'.format(steam_id)
                params.append(uploaded_by_param)

                #  await ctx.send("{} + {}".format(endpoint, '&'.join(params)))
                r = await self._bc_get_request(guild, endpoint, params=params, auth_token=auth_token)

                # await ctx.send("<https://ballchasing.com/api{}?{}>".format(endpoint, '&'.join(params)))

                params.remove(uploaded_by_param)
                data = r.json()

                # checks for correct replays
                oran_wins = 0
                blue_wins = 0
                replay_ids = []
                if 'list' in data:
                    await game.textChannel.send("{} has {} replays uploaded...".format(player.name, len(data['list'])))
                    for replay in data['list']:
                        await sm_game.textChannel.send("{} replays found.".format(len(replay_ids)))
                        winner = await self._is_six_mans_replay(guild, player, game, replay)
                        if winner == 'blue':
                            blue_wins += 1
                        elif winner == 'orange':
                            oran_wins += 1
                        else:
                            await game.textChannel.send("Winner not defined :/")
                            break
                        replay_ids.append(replay['id'])

                    series_summary = "**Blue** {blue_wins} - {oran_wins} **Orange**".format(
                        blue_wins=blue_wins, oran_wins=oran_wins
                    )

                    if replay_ids:
                        await sm_game.textChannel.send(":)")
                        return replay_ids, series_summary
            
        return None

    # good
    async def _download_replays(self, guild, replay_ids):
        auth_token = await self._get_auth_token(guild)
        tmp_replay_files = []
        this_game = 1
        for replay_id in replay_ids[::-1]:
            endpoint = "/replays/{}/file".format(replay_id)
            r = await self._bc_get_request(guild, endpoint, auth_token=auth_token)
            
            # replay_filename = "Game {}.replay".format(this_game)
            replay_filename = "{}.replay".format(replay_id)
            
            tf = tempfile.NamedTemporaryFile()
            tf.name += ".replay"
            tf.write(r.content)
            tmp_replay_files.append(tf)
            this_game += 1

        return tmp_replay_files

    # good
    async def _upload_replays(self, guild, subgroup_id, files_to_upload):
        endpoint = "/v2/upload"
        params = [
            'visibility={}'.format(config.visibility),
            'group={}'.format(subgroup_id)
        ]
        auth_token = await self._get_auth_token(guild)

        replay_ids_in_group = []
        for replay_file in files_to_upload:
            replay_file.seek(0)
            files = {'file': replay_file}

            r = await self._bc_post_request(guild, endpoint, params, auth_token=auth_token, files=files)
        
            status_code = r.status_code
            data = r.json()
            
            try:
                if status_code == 201:
                    replay_ids_in_group.append(data['id'])
                elif status_code == 409: # Handle duplicate replays
                    patch_endpoint = '/replays/{}/'.format(data['id'])
                    r = await self._bc_patch_request(ctx, patch_endpoint, auth_token=auth_token, json={'group': subgroup_id, 'visibility': config.visibility})
                    if r.status_code == 204:
                        replay_ids_in_group.append(data['id'])
            except:
                pass
                # await ctx.send(":x: {} error: {}".format(status_code, data['error']))
            
            replay_file.close()
        
        return replay_ids_in_group

    async def _add_replay_to_group(self, guild, replay_id, subgroup_id, auth_token=None):
        pass

    # guild
    async def _rename_replays(self, guild, uploaded_replays_ids):
        auth_token = await self._get_auth_token(guild)
        renamed = []

        game_number = 1
        for replay_id in uploaded_replays_ids:
            endpoint = '/replays/{}'.format(replay_id)
            payload = {
                'title': 'Game {}'.format(game_number)
            }
            r = await self._bc_patch_request(guild, endpoint, auth_token=auth_token, json=payload)
            status_code = r.status_code

            if status_code == 204:
                renamed.append(replay_id)            
            else:
                await ctx.send(":x: {} error.".format(status_code))

            game_number += 1
        return renamed

    async def _get_auth_token(self, guild):
        return await self.config.guild(guild).AuthToken()
    
    async def _save_auth_token(self, ctx, token):
        await self.config.guild(ctx.guild).AuthToken.set(token)
        return True

    async def _get_top_level_group(self, guild):
        return await self.config.guild(guild).TopLevelGroup()
    
    async def _save_top_level_group(self, guild, group_id):
        await self.config.guild(guild).TopLevelGroup.set(group_id)
        return True
    
    async def _get_account_register(self, guild):
        return await self.config.guild(guild).AccountRegister()
    
    async def _save_account_register(self, guild, account_register):
        await self.config.guild(guild).AccountRegister.set(account_register)
        return True


class Observer(metaclass=abc.ABCMeta):
    def __init__(self):
        pass
    
    @abc.abstractmethod
    def update(self, arg):
        pass
    
