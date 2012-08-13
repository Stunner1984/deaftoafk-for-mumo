#!/usr/bin/env python
# -*- coding: utf-8

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
                                ('filename_status', str, '/tmp/deaftoafk.status_'),
				('removed_channel_info', str, 'The channel you were in before afk was removed; you have been moved into the default channel.')
                                )
                    }
    
    def __init__(self, name, manager, configuration = None):
        MumoModule.__init__(self, name, manager, configuration)
        self.murmur = manager.getMurmurModule()
	
    def writeState(self, statusobj, serverid):
        try:
            scfg = getattr(self.cfg(), 'server_%d' % int(serverid))
        except AttributeError:
            scfg = self.cfg().all

        filename=scfg.filename_status

	filehandle = open(filename+str(serverid), 'wb')
	pickle.dump(statusobj, filehandle)
	filehandle.close()
    
    def readState(self, serverid):
	try:
            scfg = getattr(self.cfg(), 'server_%d' % int(serverid))
        except AttributeError:
            scfg = self.cfg().all
	
	filename=scfg.filename_status
	
	try:
	    filehandle = open(filename+str(serverid), 'rb')
	    statusobj=pickle.load(filehandle)
	    filehandle.close()
	except:
	    statusobj={}
	    dict_reg={}
	    dict_unreg={}
	    statusobj["registered"]=list_reg
	    statusobj["unregistered"]=list_unreg
	return statusobj
    
    def isregistered(self, userid):
        if (userid=-1):
	  return False
	else
	  return True
    
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

	if isregistered(state.userid): #User is registered
	    statusobj=self.readState(server.id())
	    
	    userdict_reg=statusobj["registered"]
	    
	    #If user is registered and in afk list and not deaf: move back to previous channel and remove user from afk list.
	    if (state.userid in userdict_reg) and (state.deaf==False):
		user=userdict_reg[state.userid]
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

		del userdict_reg[state.userid]
		statusobj["registered"]=userdict_reg
		self.writeState(statusobj, server.id())

    def userDisconnected(self, server, state, context = None): 
	'''Only remove from afk list if not registered'''
	if not isregistered(state.userid):
	    statusobj=self.readState(server.id())
	    userdict_unreg=statusobj["unregistered"]
	    del userdict_unreg[state.session]
	    statusobj["unregistered"]=userdict_unreg
	    self.writeState(statusobj, server.id())
	    self.log().debug("userDisconnected: Removed session %s (%s) from idle list because unregistered." % (state.session, state.name))
	    
    def userStateChanged(self, server, state, context = None):
        """Move deafened users to afk channel"""
        try:
            scfg = getattr(self.cfg(), 'server_%d' % server.id())
        except AttributeError:
            scfg = self.cfg().all
       
	statusobj=self.readState(server.id())
	userdict_reg=statusobj["registered"]
	userdict_unreg=statusobj["unregistered"]
	
	if isregistered(state.userid):
	    is_registered=True
	    
	if (is_registered):
	    #Use userid for unique users.
	    identify_by=state.userid
	    
	    if (state.selfDeaf==True) and (identify_by not in userdict_reg]):
		is_new=True
		
	    if (state.selfDeaf==False) and (identify_by in userdict_unreg):
	        is_in_and_nodeaf=True

	else:
	    #Use session id for unique users.
	    identify_by=state.session
	    	    
	    if (state.selfDeaf==True) and (identify_by not in userdict_reg):
	        is_new=True
	        
	    if (state.selfDeaf==False) and (identify_by in userdict_unreg):
	        is_in_and_nodeaf=True

        if (is_new):
	    if (is_registered):
	        userdict_reg[identify_by]={}
	        userdict_reg[identify_by]["channel"]=state.channel
		userdict_reg[identify_by]["suppress"]=state.suppress
	    else:
	        userdict_unreg[identify_by]={}
	        userdict_unreg[identify_by]["channel"]=state.channel
		userdict_unreg[identify_by]["suppress"]=state.suppress
	    
	    self.log().debug("Deafened: Moved user '%s' from channelid %s into AFK." % (state.name, state.channel)) 

	    state.channel=scfg.idlechannel
	    server.setState(state)

	    statusobj["registered"]=userdict_reg
	    statusobj["unregistered"]=userdict_unreg
  	    self.writeState(statusobj, server.id())

	#if (state.selfDeaf==False) and (identify_by in userlist_state_before):
	if (is_in_and_nodeaf): #User is in one of the lists and is not deaf anymore.
	    if (is_registered):
	        user=userdict_reg[identify_by]
	    else:
		user=userdict_unreg[identify_by]
		
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

            if (is_registered):
	        del userdict_reg[identify_by]
	    else:
		del userdict_unreg[identify_by]
            
	    statusobj["registered"]=userdict_reg
	    statusobj["unregistered"]=userdict_unreg
  	    self.writeState(statusobj, server.id())

    def channelCreated(self, server, state, context = None): pass
    def channelRemoved(self, server, state, context = None):
      #Check if a user has been inside the removed channel; if so, add note to move him back to defaultchannel.
      self.log().debug("Channel FIXME has been removed, FIXME")
      
    def channelStateChanged(self, server, state, context = None): pass     
