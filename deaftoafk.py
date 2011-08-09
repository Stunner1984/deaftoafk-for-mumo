#!/usr/bin/env python
# -*- coding: utf-8
# Last edited 2011-08-09
# Version 0.0.7

# Copyright (C) 2011 Stefan Hacker <dd0t@users.sourceforge.net>
# Copyright (C) 2011 Natenom <natenom@googlemail.com>
# All rights reserved.
#
# This script is based on the scripts onjoin.py, idlemove.py and seen.py
# (made by dd0t) from the Mumble Moderator project , available at
# http://gitorious.org/mumble-scripts/mumo
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions
# are met:

# - Redistributions of source code must retain the above copyright notice,
#   this list of conditions and the following disclaimer.
# - Redistributions in binary form must reproduce the above copyright notice,
#   this list of conditions and the following disclaimer in the documentation
#   and/or other materials provided with the distribution.
# - Neither the name of the Mumble Developers nor the names of its
#   contributors may be used to endorse or promote products derived from this
#   software without specific prior written permission.

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
import pickle
import re

class deaftoafk(MumoModule):
    default_config = {'deaftoafk':(
                                ('servers', commaSeperatedIntegers, []),
                                ),
                                lambda x: re.match('(all)|(server_\d+)', x):(                                
                                ('idlechannel', int, 0),
                                ('state_before_registered', str, '/tmp/deaftoafk.sbreg_'),
                                ('state_before_unregistered', str, '/tmp/deaftoafk.sbunreg_'),
				('removed_channel_info', str, 'The channel you were in before afk was removed; you have been moved into the default channel.')
                                )
                    }
    
    def __init__(self, name, manager, configuration = None):
        MumoModule.__init__(self, name, manager, configuration)
        self.murmur = manager.getMurmurModule()
        
    def getStatebefore(self, userid, serverid):
	try:
            scfg = getattr(self.cfg(), 'server_%d' % int(serverid))
        except AttributeError:
            scfg = self.cfg().all
	if (userid==-1): #User not registered
            filename=scfg.state_before_unregistered
	else: #User is registered
	    filename=scfg.state_before_registered

	try:
	    filehandle = open(filename+str(serverid), 'rb')
	    statebefore=pickle.load(filehandle)
	    filehandle.close()
	except:
	    statebefore={}
	return statebefore
  
    def writeStatebefore(self, userid, value, serverid):
        try:
            scfg = getattr(self.cfg(), 'server_%d' % int(serverid))
        except AttributeError:
            scfg = self.cfg().all

	if (userid==-1): #User not registered
            filename=scfg.state_before_unregistered
        else: #User is registered
            filename=scfg.state_before_registered

	filehandle = open(filename+str(serverid), 'wb')
	pickle.dump(value, filehandle)
	filehandle.close()
     
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
            scfg = getattr(self.cfg(), 'server_%d' % int(serverid))
        except AttributeError:
            scfg = self.cfg().all

	if (state.userid>0): #User is registered
	    userlist_state_before=self.getStatebefore(state.userid, server.id())
	    
	    #If user is registered and in afk list and not deaf: move back to previous channel and remove user from afk list.
	    if (state.userid in userlist_state_before) and (state.deaf==False):
		user=userlist_state_before[state.userid]
		state.channel=user["channel"]

		try:
		    server.setState(state)
		    state.suppress=user["suppress"]
		    server.setState(state)
		except self.murmur.invalidChannelException:
		    self.log().debug("Channel where user %s was before does not exist anymore" % state.name)
		    state.channel=int(server.getConf("defaultchannel"))
                    server.setState(state)
                    server.sendMessage(state.session, scfg.removed_channel_info)

		del userlist_state_before[state.userid]
		self.writeStatebefore(state.userid, userlist_state_before, server.id())

    def userDisconnected(self, server, state, context = None): 
	#Only remove from afk list if not registered
	if (state.userid==-1): #User is not registered
	    userlist_state_before=self.getStatebefore(state.userid, server.id())

	    if (state.session in userlist_state_before):
		del userlist_state_before[state.session]
		self.writeStatebefore(state.userid, userlist_state_before, server.id())
		self.log().debug("userDisconnected: Removed session %s (%s) from idle list because unregistered." % (state.session, state.name))
	    
    def userStateChanged(self, server, state, context = None):
        """Move deafened users to afk channel"""
        try:
            scfg = getattr(self.cfg(), 'server_%d' % server.id())
        except AttributeError:
            scfg = self.cfg().all
       
	userlist_state_before=self.getStatebefore(state.userid, server.id())

	if (state.userid==-1):
	    tosave=state.session
	else:
	    tosave=state.userid

        if (state.selfDeaf==True) and (tosave not in userlist_state_before):
  	    user={}
  	    user["channel"]=state.channel
	    user["suppress"]=state.suppress
	    userlist_state_before[tosave]=user
	    
	    self.log().debug("Deafened: Moved user '%s' from channelid %s into AFK." % (state.name, state.channel)) 

	    state.channel=scfg.idlechannel
	    server.setState(state)

  	    self.writeStatebefore(state.userid, userlist_state_before, server.id())

	if (state.selfDeaf==False) and (tosave in userlist_state_before):
	    user=userlist_state_before[tosave]
	    
            #Only switch back to previous channel if user is still in AFK channel.
	    if (state.channel==scfg.idlechannel):
		state.channel=user["channel"]

		try:
		    server.setState(state)
		
		    #Unsuppress doesn't work if set before moved to target.
		    state.suppress=user["suppress"]
		    server.setState(state)
		    self.log().debug("Undeafened: Moved user '%s' back into channelid %s." % (state.name, user["channel"]))
	        except self.murmur.InvalidChannelException:
                    self.log().debug("Channel where user %s was before does not exist anymore, will move him to default channel." % state.name)
		    state.channel=int(server.getConf("defaultchannel"))
		    server.setState(state)
		    server.sendMessage(state.session, scfg.removed_channel_info)

            del userlist_state_before[tosave]

	    self.writeStatebefore(state.userid, userlist_state_before, server.id())

    def channelCreated(self, server, state, context = None): pass
    def channelRemoved(self, server, state, context = None): pass
    def channelStateChanged(self, server, state, context = None): pass     
