#!/usr/bin/env python
# -*- coding: utf-8
# Last edited 2011-07-22
# Version 0.0.2

# Copyright (C) 2011 Stefan Hacker <dd0t@users.sourceforge.net>
# Copyright (C) 2011 Natenom <natenom@googlemail.com>
# All rights reserved.
#
# Antirec is based on the scripts onjoin.py, idlemove.py and seen.py
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
                                ('sessions_allowed', str, '/tmp/deaftoafk.sessions_'),
                                ('state_before', str, '/tmp/deaftoafk.statebefore_')
                                )
                    }
    
    def __init__(self, name, manager, configuration = None):
        MumoModule.__init__(self, name, manager, configuration)
        self.murmur = manager.getMurmurModule()
        
    def getStatebefore(self, serverid):
        try:
            scfg = getattr(self.cfg(), 'server_%d' % int(serverid))
        except AttributeError:
            scfg = self.cfg().all
	try:
	    filehandle = open(scfg.state_before+str(serverid), 'rb')
	    statebefore=pickle.load(filehandle)
	    filehandle.close()
	except:
	    statebefore={}
	return statebefore
  
    def writeStatebefore(self, value, serverid):
        try:
            scfg = getattr(self.cfg(), 'server_%d' % int(serverid))
        except AttributeError:
            scfg = self.cfg().all
	filehandle = open(scfg.state_before+str(serverid), 'wb')
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
    def userConnected(self, server, state, context = None): pass
    def userDisconnected(self, server, state, context = None): 
	channel_before_afk=self.getStatebefore(server.id())
	if (state.session in channel_before_afk):
	    del channel_before_afk[state.session]
	    self.writeStatebefore(channel_before_afk, server.id())
	    self.log().debug("Removed session %s (%s) from idle list." % (state.session, state.name))
	    
    def userStateChanged(self, server, state, context = None):
        """Wer sich staub stellt, wird in AFK verschoben"""
        try:
            scfg = getattr(self.cfg(), 'server_%d' % server.id())
        except AttributeError:
            scfg = self.cfg().all
        
	channel_before_afk=self.getStatebefore(server.id())

        if (state.selfDeaf==True) and (state.session not in channel_before_afk):
	    self.log().debug("Moving user %s from channelid %s into AFK." % (state.name, state.channel)) 
	    channel_before_afk[state.session]=state.channel
	    state.channel=scfg.idlechannel
	    server.setState(state)
  	    self.writeStatebefore(channel_before_afk, server.id())

	if (state.selfDeaf==False) and (state.session in channel_before_afk):
	    self.log().debug("Removing session %s and moving user %s back into channelid %s." % (state.session, state.name, channel_before_afk[state.session]))
   	    state.channel = channel_before_afk[state.session]
	    server.setState(state)
	    del channel_before_afk[state.session]
	    self.writeStatebefore(channel_before_afk, server.id())

    def channelCreated(self, server, state, context = None): pass
    def channelRemoved(self, server, state, context = None): pass
    def channelStateChanged(self, server, state, context = None): pass     
