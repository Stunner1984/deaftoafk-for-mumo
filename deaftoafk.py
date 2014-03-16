#!/usr/bin/env python
# -*- coding: utf-8
#
# Copyright (C) 2011 Stefan Hacker <dd0t@users.sourceforge.net>
# Copyright (C) 2012-2014 Natenom <natenom@googlemail.com>
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions
# are met:
#
# - Redistributions of source code must retain the above copyright notice,
#   this list of conditions and the following disclaimer.
# - Redistributions in binary form must reproduce the above copyright notice,
#   this list of conditions and the following disclaimer in the documentation
#   and/or other materials provided with the distribution.
# - Neither the name of the Mumble Developers nor the names of its
#   contributors may be used to endorse or promote products derived from this
#   software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# `AS IS'' AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
# A PARTICULAR PURPOSE ARE DISCLAIMED.  IN NO EVENT SHALL THE FOUNDATION OR
# CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL,
# EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO,
# PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR
# PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF
# LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING
# NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
# SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
#
# deaftoafk.py
# This module moves self deafened users into the afk channel and moves them back
# into their previous channel when they undeaf themselfes.
#

from mumo_module import (commaSeperatedIntegers,
                         MumoModule)
import re

class deaftoafk(MumoModule):
    default_config = {'deaftoafk':(
                                ('servers', commaSeperatedIntegers, []),
                                ),
                                lambda x: re.match('(all)|(server_\d+)', x):(                                
                                ('idlechannel', int, 0),
                                ('excluded_for_afk', str, 'excludedafk'),
				('removed_channel_info', str, 'The channel you were in before afk was removed; you have been moved into the default channel.')
                                )
                    }
    
    def __init__(self, name, manager, configuration = None):
        MumoModule.__init__(self, name, manager, configuration)
        self.murmur = manager.getMurmurModule()
        self.data = {}
	
    def isregistered(self, userid):
        if (userid == -1):
	  return False
	else:
	  return True
	  
    def isexcluded(self, server, userid):
        '''Checks if userid is member of the excluded_for_afk group in the root channel'''
        try:
            scfg = getattr(self.cfg(), 'server_%d' % int(server.id()))
        except AttributeError:
            scfg = self.cfg().all
                
        ACL = server.getACL(0)
        
        for group in ACL[1]:
            if (group.name == scfg.excluded_for_afk):
                if (userid in group.members):
                    return True
                    
        return False
    
    def connected(self):
        manager = self.manager()
        log = self.log()
        log.debug("Register for Server callbacks")
        
        servers = self.cfg().deaftoafk.servers
        if not servers:
            servers = manager.SERVERS_ALL
            
        manager.subscribeServerCallbacks(self, servers)
    
    def disconnected(self): pass
    
    #
    #--- Server callback functions
    #
    def userTextMessage(self, server, user, message, current=None): pass
    def userConnected(self, server, state, context = None):
	try:
            scfg = getattr(self.cfg(), 'server_%d' % int(server.id()))
        except AttributeError:
            scfg = self.cfg().all

	if self.isregistered(state.userid): #User is registered
	    userdict_reg = self.data[server.id][0]
	    
	    #If user is registered and in afk list and not deaf: move back to previous channel and remove user from afk list.
	    if (state.userid in userdict_reg) and (state.deaf == False):
		user = userdict_reg[state.userid]
		state.channel = user["channel"]

		try:
		    server.setState(state)
		    state.suppress = user["suppress"]
		    server.setState(state)
		except self.murmur.InvalidChannelException:
		    self.log().debug("Channel where user %s was before does not exist anymore" % state.name)
		    state.channel = int(server.getConf("defaultchannel"))
                    server.setState(state)
                    server.sendMessage(state.session, scfg.removed_channel_info)

		del userdict_reg[state.userid]
		self.data[server.id][0] = userdict_reg

    def userDisconnected(self, server, state, context = None): 
	'''Only remove from afk list if not registered'''
	if not self.isregistered(state.userid): 
	    userdict_unreg = self.data[server.id][1]

	    if state.session in userdict_unreg:
		del userdict_unreg[state.session]
		self.log().debug("userDisconnected: Removed session %s (%s) from idle list because unregistered." % (state.session, state.name))

		self.data[server.id][1] = userdict_unreg
	    
    def userStateChanged(self, server, state, context = None):
        """Move deafened users to afk channel"""
        try:
            scfg = getattr(self.cfg(), 'server_%d' % server.id())
        except AttributeError:
            scfg = self.cfg().all
       
        if self.isexcluded(server, state.userid):
            return
            
        if server.id not in self.data:
	    self.data[server.id] = []
	    dict_reg = {}
	    dict_unreg = {}
	    self.data[server.id].append(dict_reg) #Accessible through self.data[sid][0]
	    self.data[server.id].append(dict_unreg) #Accessible through self.data[sid][1]
	    
        #default values
        is_new = False 
        is_in_and_nodeaf = False
       
	userdict_reg = self.data[server.id][0]
	userdict_unreg = self.data[server.id][1]
	
	if self.isregistered(state.userid):
	    is_registered = True
	else:
	    is_registered = False
	
	if (is_registered):
	    #Use userid for unique users.
	    identify_by = state.userid
	    
	    if (state.selfDeaf == True) and (identify_by not in userdict_reg):
		is_new = True
		
	    if (state.selfDeaf == False) and (identify_by in userdict_reg):
	        is_in_and_nodeaf = True

	else:
	    #Use session id for unique users.
	    identify_by = state.session
	    	    
	    if (state.selfDeaf == True) and (identify_by not in userdict_unreg):
	        is_new = True
	        
	    if (state.selfDeaf == False) and (identify_by in userdict_unreg):
	        is_in_and_nodeaf = True

        if (is_new and state.channel != scfg.idlechannel):
	    if (is_registered):
	        userdict_reg[identify_by] = {}
	        userdict_reg[identify_by]["channel"] = state.channel
		userdict_reg[identify_by]["suppress"] = state.suppress
	    else:
	        userdict_unreg[identify_by] = {}
	        userdict_unreg[identify_by]["channel"] = state.channel
		userdict_unreg[identify_by]["suppress"] = state.suppress
	    
	    self.log().debug("Deafened: Moved user '%s' from channelid %s into AFK." % (state.name, state.channel)) 

	    state.channel = scfg.idlechannel
	    server.setState(state)

	    self.data[server.id][0] = userdict_reg
	    self.data[server.id][1] = userdict_unreg
	    
	if (is_in_and_nodeaf): #User is in one of the lists and is not deaf anymore.
	    if (is_registered):
	        user = userdict_reg[identify_by]
	    else:
		user = userdict_unreg[identify_by]

            #Only switch back to previous channel if user is still in AFK channel.
	    if (state.channel == scfg.idlechannel):
		state.channel = user["channel"]

		try:
		    server.setState(state)
		    state.suppress = user["suppress"] #Unsuppress state must be set after moving user back to his channel
		    server.setState(state)
		    self.log().debug("Undeafened: Moved user '%s' back into channelid %s." % (state.name, user["channel"]))
	        except self.murmur.InvalidChannelException:
                    self.log().debug("Channel where user %s was before does not exist anymore, will move him to default channel." % state.name)
		    state.channel = int(server.getConf("defaultchannel"))
		    server.setState(state)
		    server.sendMessage(state.session, scfg.removed_channel_info)

		try:
		    if (user["message"] == "chanremoved"):
			server.sendMessage(state.session, scfg.removed_channel_info)
		except KeyError:
		    pass

                if (is_registered):
	            del userdict_reg[identify_by]
	        else:
		    del userdict_unreg[identify_by]
            
	    self.data[server.id][0] = userdict_reg
	    self.data[server.id][1] = userdict_unreg

    def channelCreated(self, server, state, context = None): pass
    def channelRemoved(self, server, state, context = None):
      '''Check if a user has been inside the removed channel; if so, replace saved channel_id into defaultchannel'''

      userdict_reg = self.data[server.id][0]
      userdict_unreg = self.data[server.id][1]

      removed_channel = state.id
      defaultchannel = int(server.getConf("defaultchannel"))
      
      for k, v in userdict_reg.items():
	  if (removed_channel == v["channel"]):
	      userdict_reg[k]["channel"] = defaultchannel
	      #self.log().debug("Userid \"%s\" was in removed channel_id '%s'. Rewrite saved channel_id to defaultchannel" % (state.name, k))
	      
	      #set message for later
	      userdict_reg[k]["message"] = "chanremoved"

      for k, v in userdict_unreg.items():
	  if (removed_channel == v["channel"]):
	      userdict_unreg[k]["channel"] = defaultchannel
	      #self.log().debug("Userid \"%s\" was in removed channel_id '%s'. Rewrite saved channel_id to defaultchannel" % (state.name, k))

	      #set message for later
	      userdict_reg[k]["message"] = "chanremoved"

      self.data[server.id][0] = userdict_reg
      self.data[server.id][1] = userdict_unreg
      
    def channelStateChanged(self, server, state, context = None): pass
