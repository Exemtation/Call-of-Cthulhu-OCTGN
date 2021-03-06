    # Python Scripts for the Call of Cthulhu LCG definition for OCTGN
    # Copyright (C) 2013  Jason Cline
    # Based heavily on the Python Scripts for the Android:Netrunner LCG definition for OCTGN
    # Copyright (C) 2012  Konstantine Thoukydides

    # This python script is free software: you can redistribute it and/or modify
    # it under the terms of the GNU General Public License as published by
    # the Free Software Foundation, either version 3 of the License, or
    # (at your option) any later version.

    # This program is distributed in the hope that it will be useful,
    # but WITHOUT ANY WARRANTY; without even the implied warranty of
    # MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    # GNU General Public License for more details.

    # You should have received a copy of the GNU General Public License
    # along with this script.  If not, see <http://www.gnu.org/licenses/>.

###==================================================File Contents==================================================###
# This file contains the autoscripting of the game. These are the actions that trigger automatically
#  when the player plays a card, double-clicks on one, or goes to Start/End ot Turn/Run
# * [Play/Trash trigger] is basically used when the a card enters or exist play in some way 
# * [Card Use trigger] is used when a card is being used while on the table. I.e. being double-clicked.
# * [Other Player trigger] is used when another player plays a card or uses an action. The other player basically do your card effect for you
# * [Start/End of Turn/Run trigger] is called at the start/end of turns or runs actions.
# * [Core Commands] is the primary place where all the autoscripting magic happens.
# * [Helper Commands] are usually shared by many Core Commands, or maybe used many times in one of them.
###=================================================================================================================###

import re

failedRequirement = True # A Global boolean that we set in case an Autoscript cost cannot be paid, so that we know to abort the rest of the script.

#------------------------------------------------------------------------------
# Play/Score/Rez/Trash trigger
#------------------------------------------------------------------------------

def executePlayScripts(card, action):
   action = action.upper() # Just in case we passed the wrong case
   debugNotify(">>> executePlayScripts() for {} with action: {}".format(card,action)) #Debug
   debugNotify("AS dict entry = {}".format(card.AutoScript,4))
   debugNotify("card.model = {}".format(card.model),4)
   global failedRequirement
   if not Automations['Play, Score and Rez']: 
      debugNotify("Exiting because automations are off", 2)
      return
   if card.AutoScript == '': 
      debugNotify("Exiting because card has no autoscripts", 2)
      return
   failedRequirement = False
   X = 0
   Autoscripts = card.AutoScript.split('||') # When playing cards, the || is used as an "and" separator, rather than "or". i.e. we don't do choices (yet)
   autoScriptsSnapshot = list(Autoscripts) # Need to work on a snapshot, because we'll be modifying the list.
   for autoS in autoScriptsSnapshot: # Checking and removing any "AtTurnStart" clicks.
      if (autoS == '' or 
          re.search(r'atTurn(Start|End)', autoS) or 
          re.search(r'atRunStart', autoS) or 
          re.search(r'Reduce[0-9#X]Cost', autoS) or 
          re.search(r'whileRunning', autoS) or 
          re.search(r'atJackOut', autoS) or 
          re.search(r'atSuccessfulRun', autoS) or 
          re.search(r'onAccess', autoS) or 
          re.search(r'Placement', autoS) or 
          re.search(r'whileInPlay', autoS) or 
          re.search(r'constantAbility', autoS) or 
          re.search(r'onPay', autoS) or # onPay effects are only useful before we go to the autoscripts, for the cost reduction.
          re.search(r'triggerNoisy', autoS) or # Trigger Noisy are used automatically during action use.
          re.search(r'-isTrigger', autoS)): Autoscripts.remove(autoS)
      elif re.search(r'excludeDummy', autoS) and card.highlight == DummyColor: Autoscripts.remove(autoS)
      elif re.search(r'onlyforDummy', autoS) and card.highlight != DummyColor: Autoscripts.remove(autoS)
      elif re.search(r'CustomScript', autoS): 
         CustomScript(card,action)
         Autoscripts.remove(autoS)
   if len(Autoscripts) == 0: return
   if debugVerbosity >= 2: notify ('Looking for multiple choice options') # Debug
   if action == 'PLAY': trigger = 'onPlay' # We figure out what can be the possible multiple choice trigger
   elif action == 'REZ': trigger = 'onRez'
   elif action == 'INSTALL': trigger = 'onInstall'
   elif action == 'SCORE': trigger = 'onScore'
   elif action == 'TRASH': trigger = 'onTrash'
   else: trigger = 'N/A'
   if debugVerbosity >= 2: notify ('trigger = {}'.format(trigger)) # Debug
   if trigger != 'N/A': # If there's a possibility of a multiple choice trigger, we do the check
      TriggersFound = [] # A List which will hold any valid abilities for this trigger
      for autoS in Autoscripts:
         if re.search(r'{}:'.format(trigger),autoS): # If the script has the appropriate trigger, we put it into the list.
            TriggersFound.append(autoS)
      if debugVerbosity >= 2: notify ('TriggersFound = {}'.format(TriggersFound)) # Debug
      if len(TriggersFound) > 1: # If we have more than one option for this trigger, we need to ask the player for which to use.
         if Automations['WinForms']: ChoiceTXT = "This card has multiple abilities that can trigger at this point.\nSelect the ones you would like to use."
         else: ChoiceTXT = "This card has multiple abilities that can trigger at this point.\nType the number of the one you would like to use."
         triggerInstructions = re.search(r'{}\[(.*?)\]'.format(trigger),card.Instructions) # If the card has multiple options, it should also have some card instructions to have nice menu options.
         if not triggerInstructions and debugVerbosity >= 1: notify("## Oops! No multiple choice instructions found and I expected some. Will crash prolly.") # Debug
         cardInstructions = triggerInstructions.group(1).split('|-|') # We instructions for trigger have a slightly different split, so as not to conflict with the instructions from AutoActions.
         choices = cardInstructions
         abilChoice = SingleChoice(ChoiceTXT, choices, type = 'button')
         if abilChoice == 'ABORT' or abilChoice == None: return # If the player closed the window, or pressed Cancel, abort.
         TriggersFound.pop(abilChoice) # What we do now, is we remove the choice we made, from the list of possible choices. We remove it because then we will remove all the other options from the main list "Autoscripts"
         for unchosenOption in TriggersFound:
            if debugVerbosity >= 4: notify (' Removing unused option: {}'.format(unchosenOption)) # Debug
            Autoscripts.remove(unchosenOption)
         if debugVerbosity >= 2: notify ('Final Autoscripts after choices: {}'.format(Autoscripts)) # Debug
   for autoS in Autoscripts:
      debugNotify("First Processing: {}".format(autoS), 2) # Debug
      effectType = re.search(r'(on[A-Za-z]+|while[A-Za-z]+):', autoS)
      if not effectType:
         debugNotify("no regeX match for playscripts. aborting",4)
         continue
      else: debugNotify("effectType.group(1)= {}".format(effectType.group(1)),4)
      if ((effectType.group(1) == 'onRez' and action != 'REZ') or # We don't want onPlay effects to activate onTrash for example.
          (effectType.group(1) == 'onPlay' and action != 'PLAY') or
          (effectType.group(1) == 'onInstall' and action != 'INSTALL') or
          (effectType.group(1) == 'onScore' and action != 'SCORE') or
          (effectType.group(1) == 'onStartup' and action != 'STARTUP') or
          (effectType.group(1) == 'onMulligan' and action != 'MULLIGAN') or
          (effectType.group(1) == 'whileScored' and ds != 'corp') or
          (effectType.group(1) == 'whileLiberated' and ds != 'runner') or
          (effectType.group(1) == 'onDamage' and action != 'DAMAGE') or
          (effectType.group(1) == 'onLiberation' and action != 'LIBERATE') or
          (effectType.group(1) == 'onTrash' and action != 'TRASH' and action!= 'UNINSTALL' and action != 'DEREZ') or
          (effectType.group(1) == 'onDerez' and action != 'DEREZ')): 
         debugNotify("Rejected {} because {} does not fit with {}".format(autoS,effectType.group(1),action))
         continue 
      if re.search(r'-isOptional', autoS):
         if not confirm("This card has an optional ability you can activate at this point. Do you want to do so?"): 
            notify("{} opts not to activate {}'s optional ability".format(me,card))
            return 'ABORT'
         else: notify("{} activates {}'s optional ability".format(me,card))
      selectedAutoscripts = autoS.split('$$')
      if debugVerbosity >= 2: notify ('selectedAutoscripts: {}'.format(selectedAutoscripts)) # Debug
      for activeAutoscript in selectedAutoscripts:
         debugNotify("Second Processing: {}".format(activeAutoscript), 2) # Debug
         if chkWarn(card, activeAutoscript) == 'ABORT': return
         if not ifHave(activeAutoscript): continue # If the script requires the playet to have a specific counter value and they don't, do nothing.
         if re.search(r'-ifAccessed', activeAutoscript) and ds != 'runner': 
            debugNotify("!!! Failing script because card is not being accessed")
            continue # These scripts are only supposed to fire from the runner (when they access a card)         
         if re.search(r'-ifActive', activeAutoscript):
            if card.highlight == InactiveColor or card.highlight == RevealedColor or card.group.name != 'Table':
               debugNotify("!!! Failing script because card is inactive. highlight == {}. group.name == {}".format(card.highlight,card.group.name))
               continue 
            else: debugNotify("Succeeded for -ifActive. highlight == {}. group.name == {}".format(card.highlight,card.group.name))
         else: debugNotify("No -ifActive Modulator")
         if re.search(r'-ifScored', activeAutoscript) and not card.markers[mdict['Scored']]:
            debugNotify("!!! Failing script because card is not scored")
            continue 
         if re.search(r'-ifUnscored', activeAutoscript) and card.markers[mdict['Scored']]:
            debugNotify("!!! Failing script because card is scored")
            continue 
         if re.search(r':Pass\b', activeAutoscript): continue # Pass is a simple command of doing nothing ^_^
         effect = re.search(r'\b([A-Z][A-Za-z]+)([0-9]*)([A-Za-z& ]*)\b([^:]?[A-Za-z0-9_&{}\|:,<> -]*)', activeAutoscript)
         debugNotify('effects: {}'.format(effect.groups()), 2) #Debug
         if effectType.group(1) == 'whileRezzed' or effectType.group(1) == 'whileInstalled' or effectType.group(1) == 'whileScored' or effectType.group(1) == 'whileLiberated':
            if action == 'STARTUP' or action == 'MULLIGAN': 
               debugNotify("Aborting while(Rezzed|Scored|etc) because we're on statup/mulligan")
               continue # We don't want to run whileRezzed events during startup
            else: debugNotify("not on statup/mulligan. proceeding")
            if effect.group(1) != 'Gain' and effect.group(1) != 'Lose': continue # The only things that whileRezzed and whileScored affect in execute Automations is GainX scripts (for now). All else is onTrash, onPlay etc
            if action == 'DEREZ' or ((action == 'TRASH' or action == 'UNINSTALL') and card.highlight != InactiveColor and card.highlight != RevealedColor): Removal = True
            else: Removal = False
         #elif action == 'DEREZ' or action == 'TRASH': continue # If it's just a one-off event, and we're trashing it, then do nothing.
         else: Removal = False
         targetC = findTarget(activeAutoscript)
         targetPL = ofwhom(activeAutoscript,card.owner) # So that we know to announce the right person the effect, affects.
         announceText = "{} uses {}'s ability to".format(targetPL,card)
         debugNotify(" targetC: {}".format(targetC), 3) # Debug
         if effect.group(1) == 'Gain' or effect.group(1) == 'Lose':
            if Removal: 
               if effect.group(1) == 'Gain': passedScript = "Lose{}{}".format(effect.group(2),effect.group(3))
               elif effect.group(1) == 'SetTo': passedScript = "SetTo{}{}".format(effect.group(2),effect.group(3))
               else: passedScript = "Gain{}{}".format(effect.group(2),effect.group(3))
            else: 
               if effect.group(1) == 'Gain': passedScript = "Gain{}{}".format(effect.group(2),effect.group(3))
               elif effect.group(1) == 'SetTo': passedScript = "SetTo{}{}".format(effect.group(2),effect.group(3))
               else: passedScript = "Lose{}{}".format(effect.group(2),effect.group(3))
            if effect.group(4): passedScript += effect.group(4)
            debugNotify("passedscript: {}".format(passedScript), 2) # Debug
            gainTuple = GainX(passedScript, announceText, card, targetC, notification = 'Quick', n = X, actionType = action)
            if gainTuple == 'ABORT': return
            X = gainTuple[1] 
         else: 
            passedScript = effect.group(0)
            debugNotify("passedscript: {}".format(passedScript), 2) # Debug
            if regexHooks['CreateDummy'].search(passedScript): 
               if CreateDummy(passedScript, announceText, card, targetC, notification = 'Quick', n = X) == 'ABORT': return
            elif regexHooks['DrawX'].search(passedScript): 
               if DrawX(passedScript, announceText, card, targetC, notification = 'Quick', n = X) == 'ABORT': return
            elif regexHooks['TokensX'].search(passedScript): 
               if TokensX(passedScript, announceText, card, targetC, notification = 'Quick', n = X) == 'ABORT': return
            elif regexHooks['RollX'].search(passedScript): 
               rollTuple = RollX(passedScript, announceText, card, targetC, notification = 'Quick', n = X)
               if rollTuple == 'ABORT': return
               X = rollTuple[1] 
            elif regexHooks['RequestInt'].search(passedScript): 
               numberTuple = RequestInt(passedScript, announceText, card, targetC, notification = 'Quick', n = X)
               if numberTuple == 'ABORT': return
               X = numberTuple[1] 
            elif regexHooks['DiscardX'].search(passedScript): 
               discardTuple = DiscardX(passedScript, announceText, card, targetC, notification = 'Quick', n = X)
               if discardTuple == 'ABORT': return
               X = discardTuple[1] 
            elif regexHooks['RunX'].search(passedScript): 
               if RunX(passedScript, announceText, card, targetC, notification = 'Quick', n = X) == 'ABORT': return
            elif regexHooks['TraceX'].search(passedScript): 
               if TraceX(passedScript, announceText, card, targetC, notification = 'Quick', n = X) == 'ABORT': return
            elif regexHooks['ReshuffleX'].search(passedScript): 
               reshuffleTuple = ReshuffleX(passedScript, announceText, card, targetC, notification = 'Quick', n = X)
               if reshuffleTuple == 'ABORT': return
               X = reshuffleTuple[1]
            elif regexHooks['ShuffleX'].search(passedScript): 
               if ShuffleX(passedScript, announceText, card, targetC, notification = 'Quick', n = X) == 'ABORT': return
            elif regexHooks['ChooseKeyword'].search(passedScript): 
               if ChooseKeyword(passedScript, announceText, card, targetC, notification = 'Quick', n = X) == 'ABORT': return
            elif regexHooks['InflictX'].search(passedScript): 
               if InflictX(passedScript, announceText, card, targetC, notification = 'Quick', n = X) == 'ABORT': return
            elif regexHooks['RetrieveX'].search(passedScript): 
               retrieveTuple = RetrieveX(passedScript, announceText, card, targetC, notification = 'Quick', n = X)
               if retrieveTuple == 'ABORT': return # Retrieve also returns the cards it found in a tuple. But we're not using those here.
               X = len(retrieveTuple[1])
            elif regexHooks['ModifyStatus'].search(passedScript): 
               if ModifyStatus(passedScript, announceText, card, targetC, notification = 'Quick', n = X) == 'ABORT': return
         if failedRequirement: break # If one of the Autoscripts was a cost that couldn't be paid, stop everything else.
         debugNotify("Loop for scipt {} finished".format(passedScript), 2)

#------------------------------------------------------------------------------
# Card Use trigger
#------------------------------------------------------------------------------

def useAbility(card, x = 0, y = 0): # The start of autoscript activation.
   debugNotify(">>> useAbility(){}".format(extraASDebug())) #Debug
   mute()
   global failedRequirement,gatheredCardList
   AutoscriptsList = [] # An empty list which we'll put the AutoActions to execute.
   failedRequirement = False # We set it to false when we start a new autoscript.
   debugNotify("Checking if Tracing card...", 4)
   if card.Type == 'Button': # The Special button cards.
      if card.name == 'Access Imminent': BUTTON_Access()
      elif card.name == 'No Rez': BUTTON_NoRez()
      elif card.name == 'Wait!': BUTTON_Wait()
      else: BUTTON_OK()
      return
   if (card._id in Stored_Type and fetchProperty(card, 'Type') == 'Tracing') or card.model == 'eb7e719e-007b-4fab-973c-3fe228c6ce20': # If the player double clicks on the Tracing card...
      debugNotify("+++ Confirmed tacting card. Checking Status...", 5)
      if card.isFaceUp and not card.markers[mdict['Credits']]: inputTraceValue(card, limit = 0)
      elif card.isFaceUp and card.markers[mdict['Credits']]: payTraceValue(card)
      elif not card.isFaceUp: card.isFaceUp = True
      return
   debugNotify("Not a tracing card. Checking highlight...", 4)
   if markerScripts(card): return # If there's a special marker, it means the card triggers to do something else with the default action
   if card.highlight == InactiveColor:
      accessRegex = re.search(r'onAccess:([^|]+)',card.AutoScript)
      if not accessRegex:
         whisper("You cannot use inactive cards. Please use the relevant card abilities to clear them first. Aborting")
         return
   debugNotify("Finished storing {}s. Checking Rez status".format(card.AutoAction), 4)
   if not card.isFaceUp:
      if re.search(r'onAccess',fetchProperty(card, 'AutoActions')) and confirm("This card has an ability that can be activated even when unrezzed. Would you like to activate that now?"): card.isFaceUp = True # Activating an on-access ability requires the card to be exposed, it it's no already.
      elif re.search(r'Hidden',fetchProperty(card, 'Keywords')): card.isFaceUp # If the card is a hidden resource, just turn it face up for its imminent use.
      elif fetchProperty(card, 'Type') == 'Agenda': 
         scrAgenda(card) # If the player double-clicks on an Agenda card, assume they wanted to Score it.
         return
      else: 
         intRez(card) # If card is face down or not rezzed assume they wanted to rez       
         return
   debugNotify("Card not unrezzed. Checking for automations switch...", 4)
   if not Automations['Play, Score and Rez'] or fetchProperty(card, 'AutoActions') == '':
      debugNotify("Going to useCard() because AA = {}".format(fetchProperty(card, 'AutoActions')))
      useCard(card) # If card is face up but has no autoscripts, or automation is disabled just notify that we're using it.
      return
   debugNotify("Automations active. Checking for CustomScript...", 4)
   if re.search(r'CustomScript', fetchProperty(card, 'AutoActions')): 
      if chkTargeting(card) == 'ABORT': return
      CustomScript(card,'USE') # Some cards just have a fairly unique effect and there's no use in trying to make them work in the generic framework.
      return
   debugNotify("+++ All checks done!. Starting Choice Parse...", 5)
   ### Checking if card has multiple autoscript options and providing choice to player.
   Autoscripts = fetchProperty(card, 'AutoActions').split('||')
   autoScriptSnapshot = list(Autoscripts)
   for autoS in autoScriptSnapshot: # Checking and removing any clickscripts which were put here in error.
      if (re.search(r'while(Rezzed|Scored)', autoS) 
         or re.search(r'on(Play|Score|Install)', autoS) 
         or re.search(r'AtTurn(Start|End)', autoS)
         or not card.isFaceUp and not re.search(r'onAccess', autoS) # If the card is still unrezzed and the ability does not have "onAccess" on it, it can't be used.
         or (re.search(r'onlyforDummy', autoS) and card.highlight != DummyColor)
         or (re.search(r'(CreateDummy|excludeDummy)', autoS) and card.highlight == DummyColor)): # Dummies in general don't create new dummies
         Autoscripts.remove(autoS)
   debugNotify("Removed bad options", 2)
   if len(Autoscripts) == 0:
      useCard(card) # If the card had only "WhileInstalled"  or AtTurnStart effect, just announce that it is being used.
      return 
   if len(Autoscripts) > 1: 
      #abilConcat = "This card has multiple abilities.\nWhich one would you like to use?\
                #\n\n(Tip: You can put multiple abilities one after the the other (e.g. '110'). Max 9 at once)\n\n" # We start a concat which we use in our confirm window.
      if Automations['WinForms']: ChoiceTXT = "This card has multiple abilities.\nSelect the ones you would like to use, in order, and press the [Finish Selection] button"
      else: ChoiceTXT = "This card has multiple abilities.\nType the ones you would like to use, in order, and press the [OK] button"
      cardInstructions = card.Instructions.split('||')
      if len(cardInstructions) > 1: choices = cardInstructions
      else:
         choices = []
         for idx in range(len(Autoscripts)): # If a card has multiple abilities, we go through each of them to create a nicely written option for the player.
            debugNotify("Autoscripts {}".format(Autoscripts), 2) # Debug
            abilRegex = re.search(r"A([0-9]+)B([0-9]+)G([0-9]+)T([0-9]+):([A-Z][A-Za-z ]+)([0-9]*)([A-Za-z ]*)-?(.*)", Autoscripts[idx]) # This regexp returns 3-4 groups, which we then reformat and put in the confirm dialogue in a better readable format.
            debugNotify("Choice Regex is {}".format(abilRegex.groups()), 2) # Debug
            if abilRegex.group(1) != '0': abilCost = 'Use {} Clicks'.format(abilRegex.group(1))
            else: abilCost = '' 
            if abilRegex.group(2) != '0': 
               if abilCost != '': 
                  if abilRegex.group(3) != '0' or abilRegex.group(4) != '0': abilCost += ', '
                  else: abilCost += ' and '
               abilCost += 'Pay {} Credits'.format(abilRegex.group(2))
            if abilRegex.group(3) != '0': 
               if abilCost != '': 
                  if abilRegex.group(4) != '0': abilCost += ', '
                  else: abilCost += ' and '
               abilCost += 'Lose {} Agenda Points'.format(abilRegex.group(3))
            if abilRegex.group(4) != '0': 
               if abilCost != '': abilCost += ' and '
               if abilRegex.group(4) == '1': abilCost += 'Trash this card'
               else: abilCost += 'Use (Once per turn)'
            if abilRegex.group(1) == '0' and abilRegex.group(2) == '0' and abilRegex.group(3) == '0' and abilRegex.group(4) == '0':
               if not re.search(r'-isCost', Autoscripts[idx]): 
                  abilCost = 'Activate' 
                  connectTXT = ' to '
               else: 
                  abilCost = '' # If the ability claims to be a cost, then we need to put it as part of it, before the "to"
                  connectTXT = ''
            else:
               if not re.search(r'-isCost', Autoscripts[idx]): connectTXT = ' to ' # If there isn't an extra cost, then we connect with a "to" clause
               else: connectTXT = 'and ' 
            if abilRegex.group(6):
               if abilRegex.group(6) == '999': abilX = 'all'
               else: abilX = abilRegex.group(6)
            else: abilX = abilRegex.group(6)
            if re.search(r'-isSubroutine', Autoscripts[idx]): 
               if abilCost == 'Activate':  # IF there's no extra costs to the subroutine, we just use the "enter" glyph
                  abilCost = uniSubroutine()
                  connectTXT = ''
               else: abilCost = '{} '.format(uniSubroutine()) + abilCost # If there's extra costs to the subroutine, we prepend the "enter" glyph to the rest of the costs.
            #abilConcat += '{}: {}{}{} {} {}'.format(idx, abilCost, connectTXT, abilRegex.group(5), abilX, abilRegex.group(7)) # We add the first three groups to the concat. Those groups are always Gain/Hoard/Prod ## Favo/Solaris/Spice
            choices.insert(idx,'{}{}{} {} {}'.format(abilCost, connectTXT, abilRegex.group(5), abilX, abilRegex.group(7)))
            if abilRegex.group(5) == 'Put' or abilRegex.group(5) == 'Remove' or abilRegex.group(5) == 'Refill': choices[idx] += ' counter' # If it's putting a counter, we clarify that.
            debugNotify("About to check rest of choice regex", 3)
            if abilRegex.group(8): # If the autoscript has an 8th group, then it means it has subconditions. Such as "per Marker" or "is Subroutine"
               subconditions = abilRegex.group(8).split('$$') # These subconditions are always separated by dashes "-", so we use them to split the string
               for idx2 in range(len(subconditions)):
                  debugNotify(" Checking subcondition {}:{}".format(idx2,subconditions[idx2]), 4)
                  if re.search(r'isCost', Autoscripts[idx]) and idx2 == 1: choices[idx] += ' to' # The extra costs of an action are always at the first part (i.e. before the $$)
                  elif idx2 > 0: choices[idx] += ' and'
                  subadditions = subconditions[idx2].split('-')
                  for idx3 in range(len(subadditions)):
                     debugNotify(" Checking subaddition {}-{}:{}".format(idx2,idx3,subadditions[idx3]), 4)
                     if re.search(r'warn[A-Z][A-Za-z0-9 ]+', subadditions[idx3]): continue # Don't mention warnings.
                     if subadditions[idx3] in IgnoredModulators: continue # We ignore modulators which are internal to the engine.
                     choices[idx] += ' {}'.format(subadditions[idx3]) #  Then we iterate through each distinct subcondition and display it without the dashes between them. (In the future I may also add whitespaces between the distinct words)
            #abilConcat += '\n' # Finally add a newline at the concatenated string for the next ability to be listed.
      abilChoice = multiChoice(ChoiceTXT, choices,card) # We use the ability concatenation we crafted before to give the player a choice of the abilities on the card.
      if abilChoice == [] or abilChoice == 'ABORT' or abilChoice == None: return # If the player closed the window, or pressed Cancel, abort.
      #choiceStr = str(abilChoice) # We convert our number into a string
      for choice in abilChoice: 
         if choice < len(Autoscripts): AutoscriptsList.append(Autoscripts[choice].split('$$'))
         else: continue # if the player has somehow selected a number that is not a valid option, we just ignore it
      debugNotify("AutoscriptsList: {}".format(AutoscriptsList), 2) # Debug
   else: AutoscriptsList.append(Autoscripts[0].split('$$'))
   prev_announceText = 'NULL'
   multiCount = 0
   for iter in range(len(AutoscriptsList)):
      debugNotify("iter = {}".format(iter), 2)
      selectedAutoscripts = AutoscriptsList[iter]
      timesNothingDone = 0 # A variable that keeps track if we've done any of the autoscripts defined. If none have been coded, we just engage the card.
      X = 0 # Variable for special costs.
      if card.highlight == DummyColor: lingering = ' the lingering effect of' # A text that we append to point out when a player is using a lingering effect in the form of a dummy card.
      else: lingering = ''
      for activeAutoscript in selectedAutoscripts:
         #confirm("Active Autoscript: {}".format(activeAutoscript)) #Debug
         ### Checking if any of the card's effects requires one or more targets first
         if re.search(r'Targeted', activeAutoscript) and findTarget(activeAutoscript) == []: return
      for activeAutoscript in selectedAutoscripts:
         debugNotify("Reached ifHave chk", 3)
         if not ifHave(activeAutoscript): continue # If the script requires the playet to have a specific counter value and they don't, do nothing.
         if re.search(r'onlyOnce',activeAutoscript) and oncePerTurn(card, silent = True) == 'ABORT': return
         targetC = findTarget(activeAutoscript)
         ### Warning the player in case we need to
         if chkWarn(card, activeAutoscript) == 'ABORT': return
         if chkTagged(activeAutoscript) == 'ABORT': return
         ### Checking the activation cost and preparing a relevant string for the announcement
         actionCost = re.match(r"A([0-9]+)B([0-9]+)G([0-9]+)T([0-9]+):", activeAutoscript) 
         # This is the cost of the card.  It starts with A which is the amount of Clicks needed to activate
         # After A follows B for Credit cost, then for aGenda cost.
         # T takes a binary value. A value of 1 means the card needs to be trashed.
         if actionCost: # If there's no match, it means we've already been through the cost part once and now we're going through the '$$' part.
            if actionCost.group(1) != '0': # If we need to use clicks
               Acost = useClick(count = num(actionCost.group(1)))
               if Acost == 'ABORT': return
               else: announceText = Acost
            else: announceText = '{}'.format(me) # A variable with the text to be announced at the end of the action.
            if actionCost.group(2) != '0': # If we need to pay credits
               reduction = reduceCost(card, 'USE', num(actionCost.group(2)))
               gatheredCardList = True # We set this to true, so that reduceCost doesn't scan the table for subsequent executions
               if reduction > 0: extraText = " (reduced by {})".format(uniCredit(reduction))  
               elif reduction < 0: extraText = " (increased by {})".format(uniCredit(abs(reduction)))
               else: extraText = ''
               Bcost = payCost(num(actionCost.group(2)) - reduction)
               if Bcost == 'ABORT': # if they can't pay the cost afterall, we return them their clicks and abort.
                  me.Clicks += num(actionCost.group(1))
                  return
               if actionCost.group(1) != '0':
                  if actionCost.group(3) != '0' or actionCost.group(4) != '0': announceText += ', '
                  else: announceText += ' and '
               else: announceText += ' '
               announceText += 'pays {}{}'.format(uniCredit(num(actionCost.group(2)) - reduction),extraText)
            if actionCost.group(3) != '0': # If we need to pay agenda points...
               Gcost = payCost(actionCost.group(3), counter = 'AP')
               if Gcost == 'ABORT': 
                  me.Clicks += num(actionCost.group(1))
                  me.counters['Credits'].value += num(actionCost.group(2))
                  return
               if actionCost.group(1) != '0' or actionCost.group(2)  != '0':
                  if actionCost.group(4) != '0': announceText += ', '
                  else: announceText += ' and '
               else: announceText += ' '
               announceText += 'liquidates {} Agenda Points'.format(actionCost.group(3))
            if actionCost.group(4) != '0': # If the card needs to be trashed...
               if (actionCost.group(4) == '2' and oncePerTurn(card, silent = True) == 'ABORT') or (actionCost.group(4) == '1' and not confirm("This action will trash the card as a cost. Are you sure you want to continue?")):
                  # On trash cost, we confirm first to avoid double-click accidents
                  me.Clicks += num(actionCost.group(1))
                  me.counters['Credits'].value += num(actionCost.group(2))
                  me.counters['Agenda Points'].value += num(actionCost.group(3))
                  return
               if actionCost.group(1) != '0' or actionCost.group(2) != '0' or actionCost.group(3) != '0': announceText += ' and '
               else: announceText += ' '
               if actionCost.group(4) == '1': announceText += 'trashes {} to use its ability'.format(card)
               else: announceText += 'activates the once-per-turn ability of{} {}'.format(lingering,card)
            else: announceText += ' to activate{} {}'.format(lingering,card) # If we don't have to trash the card, we need to still announce the name of the card we're using.
            if actionCost.group(1) == '0' and actionCost.group(2) == '0' and actionCost.group(3) == '0' and actionCost.group(4) == '0':
               if card.Type == 'ICE': announceText = '{} activates {}'.format(me, card)
               else: announceText = '{} uses the ability of{} {}'.format(me, lingering, card)
            if re.search(r'-isSubroutine', activeAutoscript): announceText = '{} '.format(uniSubroutine()) + announceText # if we are in a subroutine, we use the special icon to make it obvious.
            announceText += ' in order to'
         elif not announceText.endswith(' in order to') and not announceText.endswith(' and'): announceText += ' and'
         debugNotify("Entering useAbility() Choice with Autoscript: {}".format(activeAutoscript), 2) # Debug
         ### Calling the relevant function depending on if we're increasing our own counters, the hoard's or putting card markers.
         if regexHooks['GainX'].search(activeAutoscript): 
            gainTuple = GainX(activeAutoscript, announceText, card, targetC, n = X)
            if gainTuple == 'ABORT': announceText == 'ABORT'
            else:
               announceText = gainTuple[0] 
               X = gainTuple[1] 
         elif regexHooks['CreateDummy'].search(activeAutoscript): announceText = CreateDummy(activeAutoscript, announceText, card, targetC, n = X)
         elif regexHooks['ReshuffleX'].search(activeAutoscript): 
            reshuffleTuple = ReshuffleX(activeAutoscript, announceText, card) # The reshuffleX() function is special because it returns a tuple.
            announceText = reshuffleTuple[0] # The first element of the tuple contains the announceText string
            X = reshuffleTuple[1] # The second element of the tuple contains the number of cards that were reshuffled from the hand in the deck.
         elif regexHooks['RetrieveX'].search(activeAutoscript): 
            retrieveTuple = RetrieveX(activeAutoscript, announceText, card, targetC, n = X)
            if retrieveTuple == 'ABORT': announceText == 'ABORT'
            else:
               announceText = retrieveTuple[0] # The first element of the tuple contains the announceText string
               X = len(retrieveTuple[1]) # The second element of the tuple contains the cards which were retrieved. by countring them we have the X
         elif regexHooks['RollX'].search(activeAutoscript): 
            rollTuple = RollX(activeAutoscript, announceText, card) # Returns like reshuffleX()
            announceText = rollTuple[0] 
            X = rollTuple[1] 
         elif regexHooks['RequestInt'].search(activeAutoscript): 
            numberTuple = RequestInt(activeAutoscript, announceText, card) # Returns like reshuffleX()
            if numberTuple == 'ABORT': announceText == 'ABORT'
            else:
               announceText = numberTuple[0] 
               X = numberTuple[1] 
         elif regexHooks['DiscardX'].search(activeAutoscript): 
            discardTuple = DiscardX(activeAutoscript, announceText, card, targetC, n = X) # Returns like reshuffleX()
            announceText = discardTuple[0] 
            X = discardTuple[1] 
         elif regexHooks['TokensX'].search(activeAutoscript):           announceText = TokensX(activeAutoscript, announceText, card, targetC, n = X)
         elif regexHooks['TransferX'].search(activeAutoscript):         announceText = TransferX(activeAutoscript, announceText, card, targetC, n = X)
         elif regexHooks['DrawX'].search(activeAutoscript):             announceText = DrawX(activeAutoscript, announceText, card, targetC, n = X)
         elif regexHooks['ShuffleX'].search(activeAutoscript):          announceText = ShuffleX(activeAutoscript, announceText, card, targetC, n = X)
         elif regexHooks['RunX'].search(activeAutoscript):              announceText = RunX(activeAutoscript, announceText, card, targetC, n = X)
         elif regexHooks['TraceX'].search(activeAutoscript):            announceText = TraceX(activeAutoscript, announceText, card, targetC, n = X)
         elif regexHooks['InflictX'].search(activeAutoscript):          announceText = InflictX(activeAutoscript, announceText, card, targetC, n = X)
         elif regexHooks['ModifyStatus'].search(activeAutoscript):      announceText = ModifyStatus(activeAutoscript, announceText, card, targetC, n = X)
         elif regexHooks['SimplyAnnounce'].search(activeAutoscript):    announceText = SimplyAnnounce(activeAutoscript, announceText, card, targetC, n = X)
         elif regexHooks['ChooseKeyword'].search(activeAutoscript):     announceText = ChooseKeyword(activeAutoscript, announceText, card, targetC, n = X)
         elif regexHooks['UseCustomAbility'].search(activeAutoscript):  announceText = UseCustomAbility(activeAutoscript, announceText, card, targetC, n = X)
         else: timesNothingDone += 1
         debugNotify("<<< useAbility() choice. TXT = {}".format(announceText), 3) # Debug
         if announceText == 'ABORT': 
            autoscriptCostUndo(card, selectedAutoscripts[0]) # If nothing was done, try to undo. The first item in selectedAutoscripts[] contains the cost.
            gatheredCardList = False
            return
         if failedRequirement: break # If part of an AutoAction could not pay the cost, we stop the rest of it.
      if announceText.endswith(' in order to'): # If our text annouce ends with " to", it means that nothing happened. Try to undo and inform player.
         autoscriptCostUndo(card, selectedAutoscripts[0])
         notify("{} but there was nothing to do.".format(announceText[:-len(' in order to')]))
      elif announceText.endswith(' and'):
         announceText = announceText[:-len(' and')] # If for some reason we end with " and" (say because the last action did nothing), we remove it.
      else: # If we did something and everything finished as expected, then take the costs.
         if re.search(r"T1:", selectedAutoscripts[0]): intTrashCard(card, fetchProperty(card,'Stat'), "free", silent = True)
      if iter == len(AutoscriptsList) - 1: # If this is the last script in the list, then we always announce the script we're running (We reduce by 1 because iterators always start as '0')
         debugNotify("Entering last notification", 2)
         if prev_announceText == 'NULL': # If it's NULL it's the only  script we run in this loop, so we just announce.
            notify("{}.".format(announceText)) # Finally announce what the player just did by using the concatenated string.
         else: # If it's not NULL, then there was a script run last time, so we check to see if it's a duplicate
            if prev_announceText == announceText: # If the previous script had the same notification output as the current one, we merge them.
               multiCount += 1
               notify("({}x) {}.".format(multiCount,announceText))
            else: # If the previous script did not have the same output as the current one, we announce them both together.
               if multiCount > 1: notify("({}x) {}.".format(multiCount,prev_announceText)) # If there were multiple versions of the last script used, announce them along with how many there were
               else: notify("{}.".format(prev_announceText))
               notify("{}.".format(announceText)) # Finally we announce the current script's concatenated notification.
      else: #if it's not the last script we run, then we just check if we should announce the previous script or just add another replication.
         debugNotify("Entering notification grouping check", 2)
         if prev_announceText == 'NULL': # If it's null, it's the first script we run in this loop...
            multiCount += 1 # ...so we don't announce but rather increase a counter and and just move to the next script, in case it's a duplicate announcement.
            prev_announceText = announceText # We also set the variable we're going to check in the next iteration, to see if it's a duplicate announcement.
         else:
            if prev_announceText == announceText: # If the previous script had the same notification output as the current one...
               multiCount += 1 # ...we merge them and continue without announcing.
            else: # If the previous script did not have the same notification output as the current one, we announce the previous one.
               if multiCount > 1: notify("({}x) {}.".format(multiCount,prev_announceText)) # If there were multiple versions of the last script used, announce them along with how many there were
               else: notify("{}.".format(prev_announceText)) 
               multiCount = 1 # We reset the counter so that we start counting how many duplicates of the current script we're going to have in the future.
               prev_announceText = announceText # And finally we reset the variable holding the previous script.
      chkNoisy(card)
      gatheredCardList = False  # We set this variable to False, so that reduceCost() calls from other functions can start scanning the table again.

#------------------------------------------------------------------------------
# Other Player trigger
#------------------------------------------------------------------------------
   
def autoscriptOtherPlayers(lookup, origin_card = "Temp", count = 1): # Function that triggers effects based on the opponent's cards.
# This function is called from other functions in order to go through the table and see if other players have any cards which would be activated by it.
# For example a card that would produce credits whenever a trace was attempted. 
   if not Automations['Triggers']: return
   debugNotify(">>> autoscriptOtherPlayers() with lookup: {}".format(lookup)) #Debug
   debugNotify("origin_card = {}".format(origin_card), 3) #Debug
   if not Automations['Play, Score and Rez']: return # If automations have been disabled, do nothing.
   for card in table:
      debugNotify('Checking {}'.format(card), 2) # Debug
      if not card.isFaceUp: continue # Don't take into accounts cards that are not rezzed.
      if card.highlight == InactiveColor: continue # We don't take into account inactive cards.
      costText = '{} activates {} to'.format(card.controller, card) 
      Autoscripts = card.AutoScript.split('||')
      debugNotify("{}'s AS: {}".format(card,Autoscripts), 4) # Debug
      autoScriptSnapshot = list(Autoscripts)
      for autoS in autoScriptSnapshot: # Checking and removing anything other than whileRezzed or whileScored.
         if not re.search(r'while(Rezzed|Scored|Running|Installed|InPlay)', autoS): 
            debugNotify("Card does not have triggered ability while in play. Aborting", 2) #Debug
            Autoscripts.remove(autoS)
         if not chkRunningStatus(autoS): Autoscripts.remove(autoS) # If the script only works while running a specific server, and we're not, then abort.
      if len(Autoscripts) == 0: continue
      for autoS in Autoscripts:
         debugNotify('Checking autoS: {}'.format(autoS), 2) # Debug
         if not re.search(r'{}'.format(lookup), autoS): 
            debugNotify("lookup: {} not found in CardScript. Aborting".format(lookup))
            continue # Search if in the script of the card, the string that was sent to us exists. The sent string is decided by the function calling us, so for example the ProdX() function knows it only needs to send the 'GeneratedSpice' string.
         if chkPlayer(autoS, card.controller,False) == 0: continue # Check that the effect's origninator is valid.
         if not ifHave(autoS,card.controller,silent = True): continue # If the script requires the playet to have a specific counter value and they don't, do nothing.
         if re.search(r'whileScored',autoS) and card.controller.getGlobalVariable('ds') != 'corp': continue # If the card is only working while scored, then its controller has to be the corp.
         if chkTagged(autoS, True) == 'ABORT': continue
         if not checkCardRestrictions(gatherCardProperties(origin_card), prepareRestrictions(autoS, 'type')): continue #If we have the '-type' modulator in the script, then need ot check what type of property it's looking for
         if not checkSpecialRestrictions(autoS,origin_card): continue #If we fail the special restrictions on the trigger card, we also abort.
         if re.search(r'onlyOnce',autoS) and oncePerTurn(card, silent = True, act = 'automatic') == 'ABORT': continue # If the card's ability is only once per turn, use it or silently abort if it's already been used
         if re.search(r'onTriggerCard',autoS): targetCard = [origin_card] # if we have the "-onTriggerCard" modulator, then the target of the script will be the original card (e.g. see Grimoire)
         else: targetCard = None
         debugNotify("Automatic Autoscripts: {}".format(autoS), 2) # Debug
         #effect = re.search(r'\b([A-Z][A-Za-z]+)([0-9]*)([A-Za-z& ]*)\b([^:]?[A-Za-z0-9_&{} -]*)', autoS)
         #passedScript = "{}".format(effect.group(0))
         #confirm('effects: {}'.format(passedScript)) #Debug
         if regexHooks['GainX'].search(autoS):
            gainTuple = GainX(autoS, costText, card, targetCard, notification = 'Automatic', n = count)
            if gainTuple == 'ABORT': break
         elif regexHooks['TokensX'].search(autoS): 
            if TokensX(autoS, costText, card, targetCard, notification = 'Automatic', n = count) == 'ABORT': break
         elif regexHooks['TransferX'].search(autoS): 
            if TransferX(autoS, costText, card, targetCard, notification = 'Automatic', n = count) == 'ABORT': break
         elif regexHooks['InflictX'].search(autoS):
            if InflictX(autoS, costText, card, targetCard, notification = 'Automatic', n = count) == 'ABORT': break
         elif regexHooks['DrawX'].search(autoS):
            if DrawX(autoS, costText, card, targetCard, notification = 'Automatic', n = count) == 'ABORT': break
         elif regexHooks['ModifyStatus'].search(autoS):
            if ModifyStatus(autoS, costText, card, targetCard, notification = 'Automatic', n = count) == 'ABORT': break
         elif regexHooks['UseCustomAbility'].search(autoS):
            if UseCustomAbility(autoS, costText, card, targetCard, notification = 'Automatic', n = count) == 'ABORT': break
   debugNotify("<<< autoscriptOtherPlayers()", 3) # Debug

#------------------------------------------------------------------------------
# Start/End of Turn/Run trigger
#------------------------------------------------------------------------------
   
def atTimedEffects(Time = 'Start'): # Function which triggers card effects at the start or end of the turn.
   mute()
   debugNotify(">>> atTimedEffects() at time: {}".format(Time)) #Debug
   global failedRequirement
   failedRequirement = False
   if not Automations['Start/End-of-Turn/Phase']: return
   TitleDone = False
   AlternativeRunResultUsed = False # Used for SuccessfulRun effects which replace the normal effect of running a server. If set to True, then no more effects on that server will be processed (to avoid 2 bank jobs triggering at the same time for example).
   X = 0
   tableCards = sortPriority([card for card in table if card.highlight != InactiveColor and card.highlight != RevealedColor])
   inactiveCards = [card for card in table if card.highlight == InactiveColor or card.highlight == RevealedColor]
   # tableCards.extend(inactiveCards) # Nope, we don't check inactive cards anymore. If they were inactive at the start of the turn, they won't trigger (See http://boardgamegeek.com/article/11686680#11686680)
   for card in tableCards:
      #if card.controller != me: continue # Obsoleted. Using the chkPlayer() function below
      if card.highlight == InactiveColor or card.highlight == RevealedColor: 
         debugNotify("Rejecting {} Because highlight == {}".format(card, card.highlight), 4)
         continue
      if not card.isFaceUp: continue
      Autoscripts = card.AutoScript.split('||')
      for autoS in Autoscripts:
         debugNotify("Processing {} Autoscript: {}".format(card, autoS), 3)
         if Time == 'Run': effect = re.search(r'at(Run)Start:(.*)', autoS) # Putting Run in a group, only to retain the search results groupings later
         elif Time == 'JackOut': effect = re.search(r'at(JackOut):(.*)', autoS) # Same as above
         elif Time == 'SuccessfulRun': effect = re.search(r'at(SuccessfulRun):(.*)', autoS) # Same as above
         elif Time == 'PreStart' or Time == 'PreEnd': effect = re.search(r'atTurn(PreStart|PreEnd):(.*)', autoS)
         else: effect = re.search(r'atTurn(Start|End):(.*)', autoS) #Putting "Start" or "End" in a group to compare with the Time variable later
         if not effect: 
            debugNotify("No effect Regex found. Aborting")
            continue
         debugNotify("Time maches. Script triggers on: {}".format(effect.group(1)), 3)
         if re.search(r'-ifSuccessfulRun', autoS):
            if Time == 'SuccessfulRun' or (Time == 'JackOut' and getGlobalVariable('SuccessfulRun') == 'True'): #If we're looking only for successful runs, we need the Time to be a successful run or jackout period.
               requiredTarget = re.search(r'-ifSuccessfulRun([A-Za-z&]+)', autoS) # We check what the script requires to be the successful target
               if getGlobalVariable('feintTarget') != 'None': currentRunTarget = getGlobalVariable('feintTarget')
               else: 
                  currentRunTargetRegex = re.search(r'running([A-Za-z&]+)', getGlobalVariable('status')) # We check what the target of the current run was.
                  currentRunTarget = currentRunTargetRegex.group(1)
               if debugVerbosity >= 2: 
                  if requiredTarget and currentRunTargetRegex: notify("!!! Regex requiredTarget: {}\n!!! currentRunTarget: {}".format(requiredTarget.groups(),currentRunTarget))
                  else: notify ("No requiredTarget or currentRunTarget regex match :(")
               if requiredTarget.group(1) == 'Any': pass # -ifSuccessfulRunAny means we run the script on any successful run (e.g. Desperado)
               elif requiredTarget.group(1) == currentRunTarget: pass # If the card requires a successful run on a server that the global variable points that we were running at, we can proceed.
               else: continue # If none of the above, it means the card script is not triggering for this server.
               debugNotify("All checked OK", 3)
            else: continue
         if chkPlayer(effect.group(2), card.controller,False) == 0: continue # Check that the effect's origninator is valid. 
         if not ifHave(autoS,card.controller,silent = True): continue # If the script requires the playet to have a specific counter value and they don't, do nothing.
         if chkTagged(autoS, True) == 'ABORT': continue
         if effect.group(1) != Time: continue # If the effect trigger we're checking (e.g. start-of-run) does not match the period trigger we're in (e.g. end-of-turn)
         debugNotify("split Autoscript: {}".format(autoS), 3)
         if debugVerbosity >= 2 and effect: notify("!!! effects: {}".format(effect.groups()))
         if re.search(r'excludeDummy', autoS) and card.highlight == DummyColor: continue
         if re.search(r'onlyforDummy', autoS) and card.highlight != DummyColor: continue
         if re.search(r'isAlternativeRunResult', effect.group(2)) and AlternativeRunResultUsed: continue # If we're already used an alternative run result and this card has one as well, ignore it
         if re.search(r'isOptional', effect.group(2)):
            extraCountersTXT = '' 
            for cmarker in card.markers: # If the card has any markers, we mention them do that the player can better decide which one they wanted to use (e.g. multiple bank jobs)
               extraCountersTXT += " {}x {}\n".format(card.markers[cmarker],cmarker[0])
            if extraCountersTXT != '': extraCountersTXT = "\n\nThis card has the following counters on it\n" + extraCountersTXT
            if not confirm("{} can have its optional ability take effect at this point. Do you want to activate it?{}".format(fetchProperty(card, 'name'),extraCountersTXT)): continue         
         if re.search(r'isAlternativeRunResult', effect.group(2)): AlternativeRunResultUsed = True # If the card has an alternative result to the normal access for a run, mark that we've used it.         
         if re.search(r'onlyOnce',autoS) and oncePerTurn(card, silent = True, act = 'automatic') == 'ABORT': continue
         splitAutoscripts = effect.group(2).split('$$')
         for passedScript in splitAutoscripts:
            targetC = findTarget(passedScript)
            if re.search(r'Targeted', passedScript) and len(targetC) == 0: 
               debugNotify("Needed target but have non. Aborting")
               continue # If our script requires a target and we can't find any, do nothing.
            if not TitleDone: 
               debugNotify("Preparing Title")
               title = None
               if Time == 'Run': title = "{}'s Start-of-Run Effects".format(me)
               elif Time == 'JackOut': title = "{}'s Jack-Out Effects".format(me)
               elif Time == 'SuccessfulRun': title = "{}'s Successful Run Effects".format(me)
               elif Time != 'PreStart' and Time != 'PreEnd': title = "{}'s {}-of-Turn Effects".format(me,effect.group(1))
               if title: notify("{:=^36}".format(title))
            TitleDone = True
            debugNotify("passedScript: {}".format(passedScript), 2)
            if card.highlight == DummyColor: announceText = "{}'s lingering effects:".format(card)
            else: announceText = "{} triggers to".format(card)
            if regexHooks['GainX'].search(passedScript):
               gainTuple = GainX(passedScript, announceText, card, targetC, notification = 'Automatic', n = X)
               if gainTuple == 'ABORT': break
               X = gainTuple[1] 
            elif regexHooks['TransferX'].search(passedScript):
               if TransferX(passedScript, announceText, card, targetC, notification = 'Automatic', n = X) == 'ABORT': break
            elif regexHooks['DrawX'].search(passedScript):
               if DrawX(passedScript, announceText, card, targetC, notification = 'Automatic', n = X) == 'ABORT': break
            elif regexHooks['RollX'].search(passedScript):
               rollTuple = RollX(passedScript, announceText, card, targetC, notification = 'Automatic', n = X)
               if rollTuple == 'ABORT': break
               X = rollTuple[1] 
            elif regexHooks['TokensX'].search(passedScript):
               if TokensX(passedScript, announceText, card, targetC, notification = 'Automatic', n = X) == 'ABORT': break
            elif regexHooks['InflictX'].search(passedScript):
               if InflictX(passedScript, announceText, card, targetC, notification = 'Automatic', n = X) == 'ABORT': break
            elif regexHooks['RetrieveX'].search(passedScript):
               retrieveTuple = RetrieveX(passedScript, announceText, card, targetC, notification = 'Automatic', n = X)
               if retrieveTuple == 'ABORT': return
               X = len(retrieveTuple[1])
            elif regexHooks['ModifyStatus'].search(passedScript):
               if ModifyStatus(passedScript, announceText, card, targetC, notification = 'Automatic', n = X) == 'ABORT': break
            elif regexHooks['DiscardX'].search(passedScript): 
               discardTuple = DiscardX(passedScript, announceText, card, targetC, notification = 'Automatic', n = X)
               if discardTuple == 'ABORT': break
               X = discardTuple[1] 
            elif regexHooks['RequestInt'].search(passedScript): 
               numberTuple = RequestInt(passedScript, announceText, card) # Returns like reshuffleX()
               if numberTuple == 'ABORT': break
               X = numberTuple[1] 
            elif regexHooks['SimplyAnnounce'].search(passedScript):
               SimplyAnnounce(passedScript, announceText, card, notification = 'Automatic', n = X)
            elif regexHooks['CustomScript'].search(passedScript):
               if CustomScript(card, action = Time) == 'ABORT': break
            if failedRequirement: break # If one of the Autoscripts was a cost that couldn't be paid, stop everything else.
   markerEffects(Time) 
   #if me.counters['Credits'].value < 0: 
      #if Time == 'Run': notify(":::Warning::: {}'s Start-of-run effects cost more Credits than {} had in their Credit Pool!".format(me,me))
      #elif Time == 'JackOut': notify(":::Warning::: {}'s Jacking-Out effects cost more Credits than {} had in their Credit Pool!".format(me,me))
      #elif Time == 'SuccessfulRun': notify(":::Warning::: {}'s Successful Run effects cost more Credits than {} had in their Credit Pool!".format(me,me))
      #else: notify(":::Warning::: {}'s {}-of-turn effects cost more Credits than {} had in their Credit Pool!".format(me,Time,me))
   #if ds == 'corp' and Time =='Start': draw(me.piles['R&D/Stack'])
   #if Time == 'SuccessfulRun' and not AlternativeRunResultUsed: # If we have a successful Run and no alternative effect was used, we ask the user if they want to automatically use one of the standard ones.
      #if getGlobalVariable('feintTarget') != 'None': currentRunTarget = getGlobalVariable('feintTarget')
      #else: 
         #currentRunTargetRegex = re.search(r'running([A-Za-z&]+)', getGlobalVariable('status')) # We check what the target of the current run was.
         #currentRunTarget = currentRunTargetRegex.group(1)
      #if currentRunTarget == 'HQ' and confirm("Rerouting to auth.level 9 corporate grid...OK\
                                             #\nAuthenticating secure credentials...OK\
                                             #\nDecrypting Home Folder...OK\
                                           #\n\nAccess to HQ Granted!\
                                             #\nWelcome back Err:::[Segmentation Fault]. Would you like to see today's priority item? \
                                           #\n\n============================\
                                             #\nAccess HQ? Y/n:"):
         #HQaccess(silent = True)
      #if currentRunTarget == 'R&D' and confirm("Processing Security Token...OK.\
                                              #\nAccess to R&D files authorized for user {}.\
                                            #\n\n============================\
                                              #\nProceed to R&D files? Y/n:".format(me.name)):
         #RDaccessX()
      #if currentRunTarget == 'Archives' and confirm("Authorization for user {} processed.\
                                                   #\nDecrypting Archive Store...OK.\
                                                #\n\n============================\
                                                  #\nRetrieve Archives? Y/n:"):
         #ARCscore()
   if TitleDone: notify(":::{:=^30}:::".format('='))   
   debugNotify("<<< atTimedEffects()", 3) # Debug
   
def markerEffects(Time = 'Start'):
   if debugVerbosity >= 1: notify(">>> markerEffects() at time: {}".format(Time)) #Debug
   cardList = [c for c in table if c.markers]
   for card in cardList:
      for marker in card.markers:
         if (Time == 'afterEngagement'
               and (re.search(r'Death from Above',marker[0])
                 or re.search(r'Vaders TIE Advance',marker[0])
                 or re.search(r'Enhancement Bonus',marker[0])
                 or re.search(r'Cocky',marker[0])
                 or re.search(r'Heavy Fire',marker[0])
                 or re.search(r'Ewok Scouted',marker[0]))):
            TokensX('Remove999'+marker[0], marker[0] + ':', card)
            notify("--> {} removes {} effect from {}".format(me,marker[0],card))
         if (Time == 'End' # Time = 'End' means End of Turn
               and (re.search(r'Defense Upgrade',marker[0])
                 or re.search(r'Force Stasis',marker[0]))):
            TokensX('Remove999'+marker[0], marker[0] + ':', card)
            notify("--> {} removes {} effect from {}".format(me,marker[0],card))
         if  (       Time == 'afterRefresh'
                  or Time == 'afterDraw'
                  or Time == 'afterDeployment'
                  or Time == 'afterConflict'
                  or Time == 'End'):
            if (     re.search(r'Munitions Expert',marker[0])
                     or re.search(r'Echo Caverns',marker[0])
                     or re.search(r'Ion Damaged',marker[0])
                     or re.search(r'Unwavering Resolve',marker[0])
                     or re.search(r'Bring Em On',marker[0])
                     or re.search(r'Shelter from the Storm',marker[0])):
               TokensX('Remove999'+marker[0], marker[0] + ':', card)
               notify("--> {} removes {} effect from {}".format(me,marker[0],card))
            if re.search(r'Secret Guardian',marker[0]): 
               returnToHand(card,silent = True)
               notify("--> {} returned Secret Guardian {} to their hand".format(me,card))
               
#------------------------------------------------------------------------------
# Redirect to Core Commands
#------------------------------------------------------------------------------
def executeAutoscripts(card,Autoscript,count = 0,action = 'PLAY',targetCards = None):
   debugNotify(">>> executeAutoscripts(){}".format(extraASDebug(Autoscript))) #Debug
   debugNotify("card = {}, count = {}, action = {}, targetCards = {}".format(card,count,action,targetCards),1)
   global failedRequirement
   failedRequirement = False
   X = count # The X Starts as the "count" passed variable which sometimes may need to be passed.
   selectedAutoscripts = Autoscript.split('$$')
   if debugVerbosity >= 2: notify ('selectedAutoscripts: {}'.format(selectedAutoscripts)) # Debug
   if re.search(r'CustomScript', Autoscript):  
      CustomScript(card,action) # If it's a customscript, we don't need to try and split it and it has its own checks.
   else: 
      for passedScript in selectedAutoscripts: 
         if chkWarn(card, passedScript) == 'ABORT': return 'ABORT'
         if chkPlayer(passedScript, card.controller,False) == 0: continue
         if re.search(r'-ifHaveForce', passedScript) and not haveForce(): 
            if debugVerbosity >= 2: notify("### Rejected -ifHaveForce script")
            continue
         if re.search(r'-ifHaventForce', passedScript) and haveForce(): 
            if debugVerbosity >= 2: notify("### Rejected -ifHaventForce script")
            continue         
         if action != 'USE' and re.search(r'onlyOnce',passedScript) and oncePerTurn(card, silent = True) == 'ABORT': continue # We don't check during 'USE' because that already checks it on first trigger.
         X = redirect(passedScript, card, action, X,targetCards)
         if failedRequirement or X == 'ABORT': return 'ABORT' # If one of the Autoscripts was a cost that couldn't be paid, stop everything else.

def redirect(Autoscript, card, action, X = 0,targetC = None):
   debugNotify(">>> redirect(){}".format(extraASDebug(Autoscript))) #Debug
   global TitleDone
   if re.search(r':Pass\b', Autoscript): return X # Pass is a simple command of doing nothing ^_^. We put it first to avoid checking for targets and so on
   if not targetC: targetC = findTarget(Autoscript,card = card)
   if not TitleDone and not (len(targetC) == 0 and re.search(r'AutoTargeted',Autoscript)): # We don't want to put a title if we have a card effect that activates only if we have some valid targets (e.g. Admiral Motti)
      Phase = re.search(r'after([A-za-z]+)',action)
      if Phase: title = "{}'s Post-{} Effects".format(me,Phase.group(1))
      else: title = "{}'s {}-of-Turn Effects".format(me,action)
      notify("{:=^36}".format(title))
      TitleDone = True
   debugNotify("card.owner = {}".format(card.owner),2)
   targetPL = ofwhom(Autoscript,card.owner) # So that we know to announce the right person the effect, affects.
   if action == 'Quick': announceText = "{} uses {}'s ability to".format(targetPL,card) 
   elif card.highlight == DummyColor: announceText = "{}'s lingering effects:".format(card)
   else: announceText = "{} uses {} to".format(targetPL,card)
   debugNotify(" targetC: {}. Notification Type = {}".format([c.name for c in targetC],'Quick'), 3) # Debug   
   if regexHooks['GainX'].search(Autoscript):
      debugNotify("in GainX hook")
      gainTuple = GainX(Autoscript, announceText, card, targetC, notification = 'Quick', n = X)
      if gainTuple == 'ABORT': return 'ABORT'
      X = gainTuple[1] 
   if regexHooks['CreateDummy'].search(Autoscript): 
      debugNotify("in CreateDummy hook")
      if CreateDummy(Autoscript, announceText, card, targetC, notification = 'Quick', n = X) == 'ABORT': return 'ABORT'
   elif regexHooks['DrawX'].search(Autoscript): 
      debugNotify("in DrawX hook")
      if DrawX(Autoscript, announceText, card, targetC, notification = 'Quick', n = X) == 'ABORT': return 'ABORT'
   elif regexHooks['RetrieveX'].search(Autoscript): 
      debugNotify("in RetrieveX hook")
      if RetrieveX(Autoscript, announceText, card, targetC, notification = 'Quick', n = X) == 'ABORT': return 'ABORT'
   elif regexHooks['TokensX'].search(Autoscript): 
      debugNotify("in TokensX hook")
      if TokensX(Autoscript, announceText, card, targetC, notification = 'Quick', n = X) == 'ABORT': return 'ABORT'
   elif regexHooks['RollX'].search(Autoscript): 
      debugNotify("in RollX hook")
      rollTuple = RollX(Autoscript, announceText, card, targetC, notification = 'Quick', n = X)
      if rollTuple == 'ABORT': return 'ABORT'
      X = rollTuple[1] 
   elif regexHooks['RequestInt'].search(Autoscript): 
      debugNotify("in RequestInt hook")
      numberTuple = RequestInt(Autoscript, announceText, card, targetC, notification = 'Quick', n = X)
      if numberTuple == 'ABORT': return 'ABORT'
      X = numberTuple[1] 
   elif regexHooks['DiscardX'].search(Autoscript): 
      debugNotify("in DiscardX hook")
      discardTuple = DiscardX(Autoscript, announceText, card, targetC, notification = 'Quick', n = X)
      if discardTuple == 'ABORT': return 'ABORT'
      X = discardTuple[1] 
   elif regexHooks['ReshuffleX'].search(Autoscript): 
      debugNotify("in ReshuffleX hook")
      reshuffleTuple = ReshuffleX(Autoscript, announceText, card, targetC, notification = 'Quick', n = X)
      if reshuffleTuple == 'ABORT': return 'ABORT'
      X = reshuffleTuple[1]
   elif regexHooks['ShuffleX'].search(Autoscript): 
      debugNotify("in ShuffleX hook")
      if ShuffleX(Autoscript, announceText, card, targetC, notification = 'Quick', n = X) == 'ABORT': return 'ABORT'
   elif regexHooks['ChooseKeyword'].search(Autoscript): 
      debugNotify("in ChooseKeyword hook")
      if ChooseKeyword(Autoscript, announceText, card, targetC, notification = 'Quick', n = X) == 'ABORT': return 'ABORT'
   elif regexHooks['ModifyStatus'].search(Autoscript): 
      debugNotify("in ModifyStatus hook")
      if ModifyStatus(Autoscript, announceText, card, targetC, notification = 'Quick', n = X) == 'ABORT': return 'ABORT'
   elif regexHooks['GameX'].search(Autoscript): 
      debugNotify("in GameX hook")
      if GameX(Autoscript, announceText, card, targetC, notification = 'Quick', n = X) == 'ABORT': return 'ABORT'
   elif regexHooks['SimplyAnnounce'].search(Autoscript): 
      debugNotify("in SimplyAnnounce hook")
      if SimplyAnnounce(Autoscript, announceText, card, targetC, notification = 'Quick', n = X) == 'ABORT': return 'ABORT'
   else: debugNotify(" No regexhook match! :(") # Debug
   debugNotify("Loop for scipt {} finished".format(Autoscript), 2)
   return X # If all went well,we return the X.

#------------------------------------------------------------------------------
# Core Commands
#------------------------------------------------------------------------------
   
def GainX(Autoscript, announceText, card, targetCards = None, notification = None, n = 0, actionType = 'USE'): # Core Command for modifying counters or global variables
   if debugVerbosity >= 1: notify(">>> GainX(){}".format(extraASDebug(Autoscript))) #Debug
   if targetCards is None: targetCards = []
   gain = 0
   extraTXT = ''
   action = re.search(r'\b(Gain|Lose|SetTo)([0-9]+)([A-Z][A-Za-z &]+)-?', Autoscript)
   if debugVerbosity >= 2: notify("### action groups: {}. Autoscript: {}".format(action.groups(0),Autoscript)) # Debug
   gain += num(action.group(2))
   targetPL = ofwhom(Autoscript, card.controller)
   if targetPL != me and not notification: otherTXT = ' force {} to'.format(targetPL)
   else: otherTXT = ''
   multiplier = per(Autoscript, card, n, targetCards) # We check if the card provides a gain based on something else, such as favour bought, or number of dune fiefs controlled by rivals.
   if action.group(1) == 'Lose': gain *= -1 
   if debugVerbosity >= 3: notify("### GainX() after per") #Debug
   gainReduce = findCounterPrevention(gain * multiplier, action.group(3), targetPL) # If we're going to gain counter, then we check to see if we have any markers which might reduce the cost.
   #confirm("multiplier: {}, gain: {}, reduction: {}".format(multiplier, gain, gainReduce)) # Debug
   if re.match(r'Reserves', action.group(3)): 
      if action.group(1) == 'SetTo': targetPL.counters['Reserves'].value = 0 # If we're setting to a specific value, we wipe what it's currently.
      targetPL.counters['Reserves'].value += gain * multiplier
      if targetPL.counters['Reserves'].value < 0: targetPL.counters['Reserves'].value = 0
   elif re.match(r'Dial', action.group(3)):
      modifyDial(gain * multiplier)
   else: 
      whisper("Gain what?! (Bad autoscript)")
      return 'ABORT'
   if debugVerbosity >= 2: notify("### Gainx() Finished counter manipulation")
   if action.group(1) == 'Gain': # Since the verb is in the middle of the sentence, we want it lowercase. 
      if action.group(3) == 'Dial': verb = 'increase'
      else: verb = 'gain'
   elif action.group(1) == 'Lose': 
      if action.group(3) == 'Dial': verb = 'decrease'
      elif re.search(r'isCost', Autoscript): verb = 'pay'
      else: verb = 'lose'
   else: verb = 'set to'
   if debugVerbosity >= 2: notify("### Gainx() Finished preparing verb ({}). Notification was: {}".format(verb,notification))
   if abs(gain) == abs(999): total = 'all' # If we have +/-999 as the count, then this mean "all" of the particular counter.
   else: total = abs(gain * multiplier) # Else it's just the absolute value which we announce they "gain" or "lose"
   if action.group(3) == 'Dial': closureTXT = "the Death Star Dial by {}".format(total)
   else: closureTXT = "{} {}".format(total, action.group(3))
   if debugVerbosity >= 2: notify("### Gainx() about to announce")
   if notification == 'Quick': announceString = "{}{} {} {}{}".format(announceText, otherTXT, verb, closureTXT,extraTXT)
   else: announceString = "{}{} {} {}{}".format(announceText, otherTXT, verb, closureTXT,extraTXT)
   if notification and multiplier > 0: notify(':> {}.'.format(announceString))
   if debugVerbosity >= 3: notify("<<< Gain() total: {}".format(total))
   return (announceString,total)
   
def TokensX(Autoscript, announceText, card, targetCards = None, notification = None, n = 0): # Core Command for adding tokens to cards
   if debugVerbosity >= 1: notify(">>> TokensX(){}".format(extraASDebug(Autoscript))) #Debug
   if targetCards is None: targetCards = []
   if re.search(r'atHost', Autoscript):
      hostCards = eval(getGlobalVariable('Host Cards'))
      for attachment in hostCards: # We check out attachments dictionary to find out who this card's host is.
         if attachment == card._id: targetCards.append(Card(hostCards[attachment]))
   if len(targetCards) == 0:
      if re.search(r'AutoTargeted',Autoscript): 
         if re.search(r'isCost', Autoscript): return 'ABORT' # If removing a token is an actual cost, then we abort the rest of the script
         else: return announceText # Otherwise we continue with the rest of the script if we only need an automatic target but have no valid one
      else: #Otherwise we just put it on ourself and assume the player forgot to target first. They can move the marker manually if they need to.
         targetCards.append(card) # If there's been to target card given, assume the target is the card itself.
         targetCardlist = ' on it' 
   else:
      targetCardlist = ' on' # A text field holding which cards are going to get tokens.
      for targetCard in targetCards:
         targetCardlist += ' {},'.format(targetCard)
   foundKey = False # We use this to see if the marker used in the AutoAction is already defined.
   action = re.search(r'\b(Put|Remove|Refill|Use|Infect|Deal|Transfer)([0-9]+)([A-Za-z: ]+)-?', Autoscript)
   debugNotify("action Regex = {}".format(action.groups()),3)
   if action.group(3) in mdict: token = mdict[action.group(3)]
   elif action.group(3) in resdict: token = resdict[action.group(3)]
   elif action.group(3) == "AnyTokenType": pass # If the removed token can be of any type, 
                                           # then we need to check which standard tokens the card has and provide the choice for one
                                           # We will do this one we start checking the target cards one-by-one.
   else: # If the marker we're looking for it not defined, then either create a new one with a random color, or look for a token with the custom name we used above.
      if action.group(1) == 'Infect': 
         victim = ofwhom(Autoscript, card.controller)
         if targetCards[0] == card: targetCards[0] = getSpecial('Affiliation',victim)
      if targetCards[0].markers:
         for key in targetCards[0].markers:
            if key[0] == action.group(3):
               foundKey = True
               token = key
      if not foundKey: # If no key is found with the name we seek, then create a new one with a random colour.
         #counterIcon = re.search(r'-counterIcon{([A-Za-z]+)}', Autoscript) # Not possible at the moment
         #if counterIcon and counterIcon.group(1) == 'plusOne':             # See https://github.com/kellyelton/OCTGN/issues/446
         #   token = ("{}".format(action.group(3)),"aa261722-e12a-41d4-a475-3cc1043166a7")         
         #else:
         rndGUID = rnd(1,8)
         token = ("{}".format(action.group(3)),"00000000-0000-0000-0000-00000000000{}".format(rndGUID)) #This GUID is one of the builtin ones
   count = num(action.group(2))
   multiplier = per(Autoscript, card, n, targetCards, notification)
   debugNotify("About to check type of module for {}".format(action.group(1)),3)
   if action.group(1) == 'Transfer':
      debugNotify("In transfer module",2)
      if len(targetCards) != 2:
         delayed_whisper(":::ERROR::: You must target exactly 2 valid cards to use this ability.")
         return 'ABORT'
      completedSeek = False
      while not completedSeek:
         if re.search(r'-sourceAny',Autoscript): 
            sourceRegex = re.search(r'-sourceAny-(.*?)-destination',Autoscript)
            sourceTargets = findTarget('Targeted-{}'.format(sourceRegex.group(1)))
         else:
            sourceRegex = re.search(r'-source(.*?)-destination',Autoscript)
            sourceTargets = findTarget('Targeted-at{}'.format(sourceRegex.group(1)))
         debugNotify("sourceRegex = {}".format(sourceRegex.groups()),2)
         if len(sourceTargets) == 0:
            delayed_whisper(":::ERROR::: No valid source card targeted.")
            return 'ABORT'
         elif len(sourceTargets) > 1:
            targetChoices = makeChoiceListfromCardList(sourceTargets)
            choiceC = SingleChoice("Choose from which card to remove the token", targetChoices, type = 'button', default = 0)
            if choiceC == 'ABORT': return 'ABORT'
            if debugVerbosity >= 4: notify("### choiceC = {}".format(choiceC)) # Debug
            sourceCard = sourceTargets.pop(choiceC)
         else: sourceCard = sourceTargets[0]
         if debugVerbosity >= 2: notify("### sourceCard = {}".format(sourceCard)) # Debug
         if re.search(r'-destinationAny',Autoscript): 
            destRegex = re.search(r'-destinationAny-(.*)',Autoscript)
            destTargets = findTarget('Targeted-{}'.format(destRegex.group(1)))
         else:
            destRegex = re.search(r'-destination(.*)',Autoscript)
            destTargets = findTarget('Targeted-at{}'.format(destRegex.group(1)))
         debugNotify("destRegex = {}".format(destRegex.groups()),2)
         if sourceCard in destTargets: destTargets.remove(sourceCard) # If the source card is targeted and also a valid destination, we remove it from the choices list.
         if len(destTargets) == 0:
            if not confirm("Your choices have left you without a valid destination to transfer the token. Try again?"): return 'ABORT'
            else: continue
         completedSeek = True #If we have a valid source and destination card, then we can exit the loop
         targetCard = destTargets[0] # After we pop() the choice card, whatever remains is the target card.
         if debugVerbosity >= 2: notify("### targetCard = {}".format(targetCard)) # Debug
      if action.group(3) == "AnyTokenType": token = chooseAnyToken(sourceCard,action.group(1))
      if count == 999: modtokens = sourceCard.markers[token] # 999 means move all tokens from one card to the other.
      else: modtokens = count * multiplier
      debugNotify("About to check if it's a basic token to remove")
      if token[0] == 'Damage' or token[0] == 'Shield' or token[0] == 'Focus':
         subMarker(sourceCard, token[0], abs(modtokens),True)
         addMarker(targetCard, token[0], modtokens,True)
      else: 
         sourceCard.markers[token] -= modtokens
         targetCard.markers[token] += modtokens
      notify("{} has moved one focus token from {} to {}".format(card,sourceCard,targetCard))
   else:
      debugNotify("In normal tokens module",2)
      for targetCard in targetCards:
         if action.group(3) == "AnyTokenType": token = chooseAnyToken(targetCard,action.group(1)) # If we need to find which token to remove, we have to do it once we know which cards we're checking.
         if action.group(1) == 'Put':
            if re.search(r'isCost', Autoscript) and targetCard.markers[token] and targetCard.markers[token] > 0 and not confirm(":::ERROR::: This card already has a {} marker on it. Proceed anyway?".format(token[0])):
               return 'ABORT'
            else: modtokens = count * multiplier
         elif action.group(1) == 'Deal': modtokens = count * multiplier
         elif action.group(1) == 'Refill': modtokens = count - targetCard.markers[token]
         elif action.group(1) == 'USE':
            if not targetCard.markers[token] or count > targetCard.markers[token]: 
               whisper("There's not enough counters left on the card to use this ability!")
               return 'ABORT'
            else: modtokens = -count * multiplier
         else: #Last option is for removing tokens.
            debugNotify("About to remove tokens",3)
            if count == 999: # 999 effectively means "all markers on card"
               if targetCard.markers[token]: count = targetCard.markers[token]
               else: 
                  if not re.search(r'isSilent', Autoscript): whisper("There was nothing to remove.")
                  count = 0
            elif re.search(r'isCost', Autoscript) and (not targetCard.markers[token] or (targetCard.markers[token] and count > targetCard.markers[token])):
               if notification != 'Automatic': whisper ("No enough markers to remove. Aborting!") #Some end of turn effect put a special counter and then remove it so that they only run for one turn. This avoids us announcing that it doesn't have markers every turn.
               debugNotify("Not enough markers to remove as cost. Aborting",2)
               return 'ABORT'
            elif not targetCard.markers[token]:
               if not re.search(r'isSilent', Autoscript): whisper("There was nothing to remove.")
               debugNotify("Found no {} tokens to remove".format(token[0]),2)
               count = 0 # If we don't have any markers, we have obviously nothing to remove.
            modtokens = -count * multiplier
         debugNotify("About to check if it's a basic token to remove")
         if token[0] == 'Damage' or token[0] == 'Shield' or token[0] == 'Focus':
            if modtokens < 0: subMarker(targetCard, token[0], abs(modtokens),True)
            else: addMarker(targetCard, token[0], modtokens,True)
         else: targetCard.markers[token] += modtokens # Finally we apply the marker modification
            
   if abs(num(action.group(2))) == abs(999): total = 'all'
   else: total = abs(modtokens)
   if re.search(r'isPriority', Autoscript): card.highlight = PriorityColor
   if action.group(1) == 'Deal': countersTXT = '' # If we "deal damage" we do not want to be writing "deals 1 damage counters"
   else: countersTXT = 'counters'
   debugNotify("About to set announceString",2)
   if action.group(1) == 'Transfer': announceString = "{} {} {} {} {} from {} to {}".format(announceText, action.group(1).lower(), total, token[0],countersTXT,sourceCard,targetCard)
   else: announceString = "{} {} {} {} {}{}".format(announceText, action.group(1).lower(), total, token[0],countersTXT,targetCardlist)
   debugNotify("About to Announce",2)
   if notification and modtokens != 0 and not re.search(r'isSilent', Autoscript): notify(':> {}.'.format(announceString))
   if debugVerbosity >= 2: notify("### TokensX() String: {}".format(announceString)) #Debug
   if debugVerbosity >= 3: notify("<<< TokensX()")
   if re.search(r'isSilent', Autoscript): return announceText # If it's a silent marker, we don't want to announce anything. Returning the original announceText will be processed by any receiving function as having done nothing.
   else: return announceString
 
def DrawX(Autoscript, announceText, card, targetCards = None, notification = None, n = 0): # Core Command for drawing X Cards from the house deck to your hand.
   if debugVerbosity >= 1: notify(">>> DrawX(){}".format(extraASDebug(Autoscript))) #Debug
   if targetCards is None: targetCards = []
   destiVerb = 'draw'
   action = re.search(r'\bDraw([0-9]+)Card', Autoscript)
   targetPL = ofwhom(Autoscript, card.controller)
   if debugVerbosity >= 3: notify("### Setting Source")
   if targetPL != me: destiVerb = 'move'
   if re.search(r'-fromDiscard', Autoscript):
      source = targetPL.piles['Discard Pile']
      sourcePath =  " from their Discard Pile"
   else: 
      source = targetPL.piles['Command Deck']
      sourcePath =  ""
   if debugVerbosity >= 3: notify("### Setting Destination")
   if re.search(r'-toDeck', Autoscript): 
      destination = targetPL.piles['Command Deck']
      destiVerb = 'move'
   elif re.search(r'-toDiscard', Autoscript):
      destination = targetPL.piles['Discard Pile']
      destiVerb = 'discard'   
   else: destination = targetPL.hand
   if debugVerbosity >= 3: notify("### Setting Destination")
   preventDraw = False
   if source == targetPL.piles['Command Deck'] and destination == targetPL.hand: # We need to look if there's card on the table which prevent card draws.
      debugNotify("About to check for Draw Prevention",2)
      for c in table:
         if preventDraw: break #If we already found a card effect which prevents draws, don't check any more cards on the table.
         Autoscripts = CardsAS.get(c.model,'').split('||')
         for autoS in Autoscripts:
            debugNotify("Checking autoS {}".format(autoS),2)
            if re.search(r'\bPreventDraw', autoS) and chkPlayer(autoS,targetPL,False) and checkOriginatorRestrictions(autoS,c):
               preventDraw = True
               notify(":> {}'s {} draw effects were blocked by {}".format(card.controller,card,c))
   if not preventDraw:
      if destiVerb == 'draw' and ModifyDraw > 0 and not confirm("You have a card effect in play that modifies the amount of cards you draw. Do you want to continue as normal anyway?\n\n(Answering 'No' will abort this action so that you can prepare for the special changes that happen to your draw."): return 'ABORT'
      draw = num(action.group(1))
      if draw == 999:
         multiplier = 1
         if currentHandSize(targetPL) >= len(targetPL.hand): # Otherwise drawMany() is going to try and draw "-1" cards which somehow draws our whole deck except one card.
            count = drawMany(source, currentHandSize(targetPL) - len(targetPL.hand), destination, True) # 999 means we refresh our hand
         else: count = 0 
         #confirm("cards drawn: {}".format(count)) # Debug
      else: # Any other number just draws as many cards.
         multiplier = per(Autoscript, card, n, targetCards, notification)
         count = drawMany(source, draw * multiplier, destination, True)
      if targetPL == me:
         if destiVerb != 'discard': destPath = " to their {}".format(destination.name)
         else: destPath = ''
      else: 
         if destiVerb != 'discard': destPath = " to {}'s {}".format(targetPL,destination.name)
         else: destPath = ''
   else: count = 0
   if debugVerbosity >= 2: notify("### About to announce.")
   if count == 0: return announceText # If there are no cards, then we effectively did nothing, so we don't change the notification.
   if notification == 'Quick': announceString = "{} draw {} cards{}".format(announceText, count,sourcePath)
   elif targetPL == me: announceString = "{} {} {} cards{}{}".format(announceText, destiVerb, count, sourcePath, destPath)
   elif source == targetPL.piles['Command Deck'] and destination == targetPL.hand: announceString = "{} {} draws {} cards.".format(announceText, targetPL, count)
   else: announceString = "{} {} {} cards from {}'s {}".format(announceText, destiVerb, count, targetPL, source.name, destPath)
   if notification and multiplier > 0: notify(':> {}.'.format(announceString))
   if debugVerbosity >= 3: notify("<<< DrawX()")
   return announceString

def DiscardX(Autoscript, announceText, card, targetCards = None, notification = None, n = 0): # Core Command for drawing X Cards from the house deck to your hand.
   if debugVerbosity >= 1: notify(">>> DiscardX(){}".format(extraASDebug(Autoscript))) #Debug
   if targetCards is None: targetCards = []
   action = re.search(r'\bDiscard([0-9]+)Card', Autoscript)
   targetPL = ofwhom(Autoscript, card.controller)
   if targetPL != me: otherTXT = ' force {} to'.format(targetPL)
   else: otherTXT = ''
   discardNR = num(action.group(1))
   if discardNR == 999:
      multiplier = 1
      discardNR = len(targetPL.hand) # 999 means we discard our whole hand
   if re.search(r'-isRandom',Autoscript): # the -isRandom modulator just discard as many cards at random.
      multiplier = per(Autoscript, card, n, targetCards, notification)
      count = handRandomDiscard(targetPL.hand, discardNR * multiplier, targetPL, silent = True)
      if re.search(r'isCost', Autoscript) and count < discardNR:
         whisper("You do not have enough cards in your hand to discard")
         return ('ABORT',0)
   else: # Otherwise we just discard the targeted cards from hand  
      multiplier = 1
      count = len(targetCards)
      if re.search(r'isCost', Autoscript) and count < discardNR:
         whisper("You do not have enough cards in your hand to discard")
         return ('ABORT',0)
      for targetC in targetCards: handDiscard(targetC)
      debugNotify("Finished discarding targeted cards from hand")
   if count == 0: 
      debugNotify("Exiting because count == 0")
      return (announceText,count) # If there are no cards, then we effectively did nothing, so we don't change the notification.
   if notification == 'Quick': announceString = "{} discards {} cards".format(announceText, count)
   else: announceString = "{}{} discard {} cards from their hand".format(announceText,otherTXT, count)
   if notification and multiplier > 0: notify(':> {}.'.format(announceString))
   if debugVerbosity >= 3: notify("<<< DiscardX()")
   return (announceString,count)
         
def ReshuffleX(Autoscript, announceText, card, targetCards = None, notification = None, n = 0): # A Core Command for reshuffling a pile into the R&D/Stack
   if debugVerbosity >= 1: notify(">>> ReshuffleX(){}".format(extraASDebug(Autoscript))) #Debug
   if targetCards is None: targetCards = []
   mute()
   X = 0
   targetPL = ofwhom(Autoscript, card.controller)
   action = re.search(r'\bReshuffle([A-Za-z& ]+)', Autoscript)
   if debugVerbosity >= 1: notify("!!! regex: {}".format(action.groups())) # Debug
   if action.group(1) == 'Hand':
      namestuple = groupToDeck(targetPL.hand, targetPL , True) # We do a silent hand reshuffle into the deck, which returns a tuple
      X = namestuple[2] # The 3rd part of the tuple is how many cards were in our hand before it got shuffled.
   elif action.group(1) == 'Discard': namestuple = groupToDeck(targetPL.piles['Discard Pile'], targetPL, True)    
   else: 
      whisper("Wat Group? [Error in autoscript!]")
      return 'ABORT'
   shuffle(targetPL.piles['Command Deck'])
   if notification == 'Quick': announceString = "{} shuffles their {} into their {}".format(announceText, namestuple[0], namestuple[1])
   else: announceString = "{} shuffle their {} into their {}".format(announceText, namestuple[0], namestuple[1])
   if notification: notify(':> {}.'.format(announceString))
   if debugVerbosity >= 3: notify("<<< ReshuffleX() return with X = {}".format(X))
   return (announceString, X)

def ShuffleX(Autoscript, announceText, card, targetCards = None, notification = None, n = 0): # A Core Command for reshuffling a pile into the R&D/Stack
   if debugVerbosity >= 1: notify(">>> ShuffleX(){}".format(extraASDebug())) #Debug
   if targetCards is None: targetCards = []
   mute()
   action = re.search(r'\bShuffle([A-Za-z& ]+)', Autoscript)
   targetPL = ofwhom(Autoscript, card.controller)
   if action.group(1) == 'Discard': pile = targetPL.piles['Discard Pile']
   elif action.group(1) == 'Deck': pile = targetPL.piles['Command Deck']
   elif action.group(1) == 'Objectives': pile = targetPL.piles['Objective Deck']
   random = rnd(10,100) # Small wait (bug workaround) to make sure all animations are done.
   shuffle(pile)
   if notification == 'Quick': announceString = "{} shuffles their {}".format(announceText, pile.name)
   elif targetPL == me: announceString = "{} shuffle their {}".format(announceText, pile.name)
   else: announceString = "{} shuffle {}' {}".format(announceText, targetPL, pile.name)
   if notification: notify(':> {}.'.format(announceString))
   if debugVerbosity >= 3: notify("<<< ShuffleX()")
   return announceString
   
def RollX(Autoscript, announceText, card, targetCards = None, notification = None, n = 0): # Core Command for drawing X Cards from the house deck to your hand.
   if debugVerbosity >= 1: notify(">>> RollX(){}".format(extraASDebug())) #Debug
   if targetCards is None: targetCards = []
   d6 = 0
   d6list = []
   result = 0
   action = re.search(r'\bRoll([0-9]+)Dice(-chk)?([1-6])?', Autoscript)
   multiplier = per(Autoscript, card, n, targetCards, notification)
   count = num(action.group(1)) * multiplier 
   for d in range(count):
      if d == 2: whisper("-- Please wait. Rolling {} dice...".format(count))
      if d == 8: whisper("-- A little while longer...")
      d6 = rolld6(silent = True)
      d6list.append(d6)
      if action.group(3): # If we have a chk modulator, it means we only increase our total if we hit a specific number.
         if num(action.group(3)) == d6: result += 1
      else: result += d6 # Otherwise we add all totals together.
      if debugVerbosity >= 2: notify("### iter:{} with roll {} and total result: {}".format(d,d6,result))
   if notification == 'Quick': announceString = "{} rolls {} on {} dice".format(announceText, d6list, count)
   else: announceString = "{} roll {} dice with the following results: {}".format(announceText,count, d6list)
   if notification: notify(':> {}.'.format(announceString))
   if debugVerbosity >= 3: notify("<<< RollX() with result: {}".format(result))
   return (announceString, result)

def RequestInt(Autoscript, announceText, card, targetCards = None, notification = None, n = 0): # Core Command for drawing X Cards from the house deck to your hand.
   if debugVerbosity >= 1: notify(">>> RequestInt(){}".format(extraASDebug(Autoscript))) #Debug
   if targetCards is None: targetCards = []
   action = re.search(r'\bRequestInt(-Min)?([0-9]*)(-div)?([0-9]*)(-Max)?([0-9]*)(-Msg)?\{?([A-Za-z0-9?$& ]*)\}?', Autoscript)
   if debugVerbosity >= 2:
      if action: notify('!!! regex: {}'.format(action.groups()))
      else: notify("!!! No regex match :(")
   if debugVerbosity >= 2: notify("### Checking for Min")
   if action.group(2): 
      min = num(action.group(2))
      minTXT = ' (minimum {})'.format(min)
   else: 
      min = 0
      minTXT = ''
   if debugVerbosity >= 2: notify("### Checking for Max")
   if action.group(6): 
      max = num(action.group(6))
      minTXT += ' (maximum {})'.format(max)
   else: 
      max = None
   if debugVerbosity >= 2: notify("### Checking for div")
   if action.group(4): 
      div = num(action.group(4))
      minTXT += ' (must be a multiple of {})'.format(div)
   else: div = 1
   if debugVerbosity >= 2: notify("### Checking for Msg")
   if action.group(8): 
      message = action.group(8)
   else: message = "{}:\nThis effect requires that you provide an 'X'. What should that number be?{}".format(fetchProperty(card, 'name'),minTXT)
   number = min - 1
   if debugVerbosity >= 2: notify("### About to ask")
   while number < min or number % div or (max and number > max):
      number = askInteger(message,min)
      if number == None: 
         whisper("Aborting Function")
         return 'ABORT'
   if debugVerbosity >= 3: notify("<<< RequestInt()")
   return (announceText, number) # We do not modify the announcement with this function.
   
def SimplyAnnounce(Autoscript, announceText, card, targetCards = None, notification = None, n = 0): # Core Command for drawing X Cards from the house deck to your hand.
   if debugVerbosity >= 1: notify(">>> SimplyAnnounce(){}".format(extraASDebug())) #Debug
   if targetCards is None: targetCards = []
   action = re.search(r'\bSimplyAnnounce{([A-Za-z0-9&,\.\' ]+)}', Autoscript)
   if debugVerbosity >= 2: #Debug
      if action: notify("!!! regex: {}".format(action.groups())) 
      else: notify("!!! regex failed :(") 
   if re.search(r'break',Autoscript) and re.search(r'subroutine',Autoscript): penaltyNoisy(card)
   if notification == 'Quick': announceString = "{} {}".format(announceText, action.group(1))
   else: announceString = "{} {}".format(announceText, action.group(1))
   if notification: notify(':> {}.'.format(announceString))
   if debugVerbosity >= 3: notify("<<< SimplyAnnounce()")
   return announceString

def CreateDummy(Autoscript, announceText, card, targetCards = None, notification = None, n = 0): # Core Command for creating dummy cards.
   if debugVerbosity >= 1: notify(">>> CreateDummy(){}".format(extraASDebug(Autoscript))) #Debug
   if targetCards is None: targetCards = []
   Dummywarn = getSetting('Dummywarn',True)
   dummyCard = None
   action = re.search(r'\bCreateDummy[A-Za-z0-9_ -]*(-with)(?!onOpponent|-doNotDiscard|-nonUnique)([A-Za-z0-9_ -]*)', Autoscript)
   # We only want this regex to be true if the dummycard is going to have tokens put on it automatically.
   if action and debugVerbosity >= 3: notify('### Regex: {}'.format(action.groups())) # debug
   elif debugVerbosity >= 3: notify('### No regex match! Aborting') # debug
   targetPL = ofwhom(Autoscript, card.controller)
   for c in table:
      if c.model == card.model and c.controller == targetPL and c.highlight == DummyColor: dummyCard = c # We check if already have a dummy of the same type on the table.
   if debugVerbosity >= 2: notify('### Checking to see what our dummy card is') # debug
   if not dummyCard or re.search(r'nonUnique',Autoscript): #Some create dummy effects allow for creating multiple copies of the same card model.
      if debugVerbosity >= 2: notify('### Dummywarn = {}'.format(Dummywarn)) # debug .
      if debugVerbosity >= 2: notify('### no dummyCard exists') # debug . Dummywarn = {}'.format(Dummywarn)
      if Dummywarn and re.search('onOpponent',Autoscript):
         if not confirm("This action creates an effect for your opponent and a way for them to remove it.\
                       \nFor this reason we've created a dummy card on the table and marked it with a special highlight so that you know that it's just a token.\
                     \n\nYou opponent can activate any abilities meant for them on the Dummy card. If this card has one, they can activate it by double clicking on the dummy. Very often, this will often remove the dummy since its effect will disappear.\
                     \n\nOnce the   dummy card is on the table, please right-click on it and select 'Pass control to {}'\
                     \n\nDo you want to see this warning again?".format(targetPL)): setSetting('Dummywarn',False)
      elif Dummywarn:
         information("This card is now supposed to go to your discard pile, but its lingering effects will only work automatically while a copy is in play.\
                       \nFor this reason we've created a dummy card on the table and marked it with a special highlight so that you know that it's just a token.\
                     \n\n(This message will not appear again.)")
         setSetting('Dummywarn',False)
      elif re.search(r'onOpponent', Autoscript): 
         if debugVerbosity >= 2: notify('### about to pop information') # debug
         information('The dummy card just created is meant for your opponent. Please right-click on it and select "Pass control to {}"'.format(targetPL))
      if debugVerbosity >= 2: notify('### Finished warnings. About to announce.') # debug
      dummyCard = table.create(card.model, playerside * 360, yaxisMove(card) + (20 * playerside * len([c for c in table if c.controller == targetPL and c.highlight == DummyColor])), 1) # This will create a fake card like the one we just created.
      dummyCard.highlight = DummyColor
   if debugVerbosity >= 2: notify('### About to move to discard pile if needed') # debug
   if not re.search(r'doNotDiscard',Autoscript): card.moveTo(card.owner.piles['Discard Pile'])
   if action: announceString = TokensX('Put{}'.format(action.group(2)), announceText,dummyCard, n = n) # If we have a -with in our autoscript, this is meant to put some tokens on the dummy card.
   else: announceString = announceText + 'create a lingering effect for {}'.format(targetPL)
   if debugVerbosity >= 3: notify("<<< CreateDummy()")
   if re.search(r'isSilent', Autoscript): return announceText
   else: return announceString # Creating a dummy isn't usually announced.

def ChooseTrait(Autoscript, announceText, card, targetCards = None, notification = None, n = 0): # Core Command for marking cards to be of a different trait than they are
   if debugVerbosity >= 1: notify(">>> ChooseTrait(){}".format(extraASDebug(Autoscript))) #Debug
   #confirm("Reached ChooseTrait") # Debug
   choiceTXT = ''
   targetCardlist = ''
   existingTrait = None
   if targetCards is None: targetCards = []
   if len(targetCards) == 0: targetCards.append(card) # If there's been to target card given, assume the target is the card itself.
   for targetCard in targetCards: targetCardlist += '{},'.format(targetCard)
   targetCardlist = targetCardlist.strip(',') # Re remove the trailing comma
   action = re.search(r'\bChooseTrait{([A-Za-z\| ]+)}', Autoscript)
   #confirm("search results: {}".format(action.groups())) # Debug
   traits = action.group(1).split('|')
   #confirm("List: {}".format(traits)) # Debug
   if len(traits) > 1:
      for i in range(len(traits)): choiceTXT += '{}: {}\n'.format(i, traits[i])
      choice = len(traits)
   else: choice = 0
   while choice > len(traits) - 1: 
      choice = askInteger("Choose one of the following traits to assign to this card:\n\n{}".format(choiceTXT),0)
      if choice == None: return 'ABORT'
   for targetCard in targetCards:
      if targetCard.markers:
         for key in targetCard.markers:
            if re.search('Trait:',key[0]):
               existingTrait = key
      if re.search(r'{}'.format(traits[choice]),targetCard.Traits): 
         if existingTrait: targetCard.markers[existingTrait] = 0
         else: pass # If the trait is anyway the same printed on the card, and it had no previous trait, there is nothing to do
      elif existingTrait:
         if debugVerbosity >= 1: notify("### Searching for {} in {}".format(traits[choice],existingTrait[0])) # Debug               
         if re.search(r'{}'.format(traits[choice]),existingTrait[0]): pass # If the trait is the same as is already there, do nothing.
         else: 
            targetCard.markers[existingTrait] = 0 
            TokensX('Put1Trait:{}'.format(traits[choice]), '', targetCard)
      else: TokensX('Put1Trait:{}'.format(traits[choice]), '', targetCard)
   if notification == 'Quick': announceString = "{} marks {} as being {} now".format(announceText, targetCardlist, traits[choice])
   else: announceString = "{} mark {} as being {} now".format(announceText, targetCardlist, traits[choice])
   if notification: notify(':> {}.'.format(announceString))
   if debugVerbosity >= 3: notify("<<< ChooseTrait()")
   return announceString
            
def ModifyStatus(Autoscript, announceText, card, targetCards = None, notification = None, n = 0): # Core Command for modifying the status of a card on the table.
   if debugVerbosity >= 1: notify(">>> ModifyStatus(){}".format(extraASDebug(Autoscript))) #Debug
   if targetCards is None: targetCards = []
   targetCardlist = '' # A text field holding which cards are going to get tokens.
   extraTXT = ''
   action = re.search(r'\b(Destroy|Exile|Capture|Rescue|Return|BringToPlay|SendToBottom|Commit|Uncommit|Engage|Disengage|Sacrifice|Attack|Takeover)(Target|Host|Multi|Myself)[-to]*([A-Z][A-Za-z&_ ]+)?', Autoscript)
   if action.group(2) == 'Myself': 
      del targetCards[:] # Empty the list, just in case.
      targetCards.append(card)
   if action.group(2) == 'Host': 
      del targetCards[:] # Empty the list, just in case.
      debugNotify("Finding Host")
      host = fetchHost(card)
      if host: targetCards = [host]
      else: 
         debugNotify("No Host Found? Aborting")
         return 'ABORT'      
   if action.group(3): dest = action.group(3)
   else: dest = 'hand'
   debugNotify("targetCards(){}".format([c.name for c in targetCards]),2) #Debug   
   for targetCard in targetCards: 
      if (action.group(1) == 'Capture' or action.group(1) == 'BringToPlay' or  action.group(1) == 'Return') and targetCard.group == table: 
         targetCardlist += '{},'.format(fetchProperty(targetCard, 'name')) # Capture saves the name because by the time we announce the action, the card will be face down.
      else: targetCardlist += '{},'.format(targetCard)
   rnd(1,10) # Dela yto be able to grab the names
   debugNotify("Preparing targetCardlist",2)      
   targetCardlist = targetCardlist.strip(',') # Re remove the trailing comma
   if action.group(1) == 'SendToBottom': # For SendToBottom, we need a different mthod, as we need to shuffle the cards.
      if action.group(2) == 'Multi': 
         debugNotify("Sending Multiple card to the bottom",3)   
         sendToBottom(targetCards)
      else: 
         debugNotify("### Sending Single card to the bottom",3)   
         try: sendToBottom([targetCards[0]])
         except: 
            delayed_whisper(":::ERROR::: You have not targeted a valid card")
            return 'ABORT'
   else:
      for targetCard in targetCards:
         if action.group(1) == 'Destroy' or action.group(1) == 'Sacrifice':
            trashResult = discard(targetCard, silent = True)
            if trashResult == 'ABORT': return 'ABORT'
            elif trashResult == 'COUNTERED': extraTXT = " (Countered!)"
         elif action.group(1) == 'Exile' and exileCard(targetCard, silent = True) != 'ABORT': pass
         elif action.group(1) == 'Return': 
            returnToHand(targetCard, silent = True)
            extraTXT = " to their owner's hand"
         elif action.group(1) == 'BringToPlay': 
            placeCard(targetCard)
            executePlayScripts(targetCard, 'PLAY') # We execute the play scripts here only if the card is 0 cost.
            autoscriptOtherPlayers('CardPlayed',targetCard)            
         elif action.group(1) == 'Capture': 
            if re.search("-captureOnMyself", Autoscript): capture(targetC = targetCard, silent = True, chosenObj = card)
            else: capture(targetC = targetCard, silent = True)
         elif action.group(1) == 'Engage': participate(targetCard, silent = True)
         elif action.group(1) == 'Disengage': clearParticipation(targetCard, silent = True)
         elif action.group(1) == 'Attack': engageTarget(targetObjective = targetCard, silent = True)
         elif action.group(1) == 'Takeover': 
            targetCard.setController(me)
            targetCard.moveToTable(0, 0 + yaxisMove(card))
         elif action.group(1) == 'Rescue': rescue(targetCard,silent = True)
         elif action.group(1) == 'Uncommit':
            if targetCard.Side == 'Light': commitColor = LightForceColor
            else: commitColor = DarkForceColor
            if targetCard.highlight == commitColor: targetCard.highlight = None
         else: return 'ABORT'
         if action.group(2) != 'Multi': break # If we're not doing a multi-targeting, abort after the first run.
   debugNotify("Finished Processing Modifications. About to announce",2)
   if notification == 'Quick': announceString = "{} {} {}{}".format(announceText, action.group(1), targetCardlist,extraTXT)
   else: announceString = "{} {} {}{}".format(announceText, action.group(1), targetCardlist, extraTXT)
   if notification and not re.search(r'isSilent', Autoscript): notify(':> {}.'.format(announceString))
   debugNotify("<<< ModifyStatus()")
   if re.search(r'isSilent', Autoscript): return announceText
   else: return announceString

def GameX(Autoscript, announceText, card, targetCards = None, notification = None, n = 0): # Core Command for alternative victory conditions
   if debugVerbosity >= 1: notify(">>> GameX(){}".format(extraASDebug(Autoscript))) #Debug
   if targetCards is None: targetCards = []
   action = re.search(r'\b(Lose|Win)Game', Autoscript)
   if debugVerbosity >= 2: #Debug
      if action: notify("!!! regex: {}".format(action.groups())) 
      else: notify("!!! regex failed :(") 
   if re.search(r'forController', Autoscript): player = card.controller
   elif re.search(r'forOwner', Autoscript): player = card.owner 
   elif re.search(r'forDark Side', Autoscript): 
      if Side == 'Dark': player = me
      else: player == opponent
   elif re.search(r'forLight Side', Autoscript): 
      if Side == 'Light': player = me
      else: player == opponent
   else: player == me
   if action.group(1) == 'Lose': 
      announceString = "=== {} loses the game! ===".format(player)
      reportGame('SpecialDefeat')
   else: 
      announceString = "=== {} wins the game! ===".format(player)
      reportGame('SpecialVictory')
   notify(announceString)
   if debugVerbosity >= 3: notify("<<< GameX()")
   return announceString

def RetrieveX(Autoscript, announceText, card, targetCards = None, notification = None, n = 0): # Core Command for finding a specific card from a pile and putting it in hand or discard pile
   if debugVerbosity >= 1: notify(">>> RetrieveX(){}".format(extraASDebug(Autoscript))) #Debug
   if targetCards is None: targetCards = []
   action = re.search(r'\bRetrieve([0-9]+)Card', Autoscript)
   targetPL = ofwhom(Autoscript, card.controller)
   if debugVerbosity >= 2: notify("### Setting Source")
   if re.search(r'-fromDiscard', Autoscript):
      source = targetPL.piles['Discard Pile']
      sourcePath =  "from their Discard Pile"
   else: 
      source = targetPL.piles['Command Deck']
      sourcePath =  "from their Command Deck"
   if debugVerbosity >= 2: notify("### Setting Destination")
   if re.search(r'-toTable', Autoscript):
      destination = table
      destiVerb = 'play'   
   else: 
      destination = targetPL.hand
      destiVerb = 'retrieve'
   if debugVerbosity >= 2: notify("### Fething Script Variables")
   count = num(action.group(1))
   multiplier = per(Autoscript, card, n, targetCards, notification)
   if source != targetPL.piles['Discard Pile']: # The discard pile is anyway visible.
      if debugVerbosity >= 2: notify("### Turning Pile Face Up")
      cover = table.create("8b5a86df-fb10-4e5e-9133-7dc03fbae22d",0,0,1,True) # Creating a dummy card to cover that player's source pile
      cover.moveTo(source) # Moving that dummy card on top of their source pile
      for c in source: c.isFaceUp = True # We flip all cards in the player's deck face up so that we can grab their properties
   restrictions = prepareRestrictions(Autoscript, seek = 'retrieve')
   cardList = []
   countRestriction = re.search(r'-onTop([0-9]+)Cards', Autoscript)
   if countRestriction: topCount = num(countRestriction.group(1))
   else: topCount = len(source)
   if count == 999: count = topCount # Retrieve999Cards means the script will retrieve all cards that match the requirements, regardless of how many there are. As such, a '-onTop#Cards' modulator should always be included.
   for c in source.top(topCount):
      if debugVerbosity >= 4: notify("### Checking card: {}".format(c))
      if checkCardRestrictions(gatherCardProperties(c), restrictions) and checkSpecialRestrictions(Autoscript,c):
         cardList.append(c)
         if re.search(r'-isTopmost', Autoscript) and len(cardList) == count: break # If we're selecting only the topmost cards, we select only the first matches we get.         
   if debugVerbosity >= 3: notify("### cardList: {}".format(cardList))
   chosenCList = []
   if len(cardList) > count:
      cardChoices = []
      cardTexts = []
      for iter in range(count):
         if debugVerbosity >= 4: notify("#### iter: {}/{}".format(iter,count))
         del cardChoices[:]
         del cardTexts[:]
         for c in cardList:
            if c.Text not in cardTexts: # we don't want to provide the player with a the same card as a choice twice.
               if debugVerbosity >= 4: notify("### Appending card")
               cardChoices.append(c)
               cardTexts.append(c.Text) # We check the card text because there are cards with the same name in different sets (e.g. Darth Vader)            
         choice = SingleChoice("Choose card to retrieve{}".format({1:''}.get(count,' {} {}'.format(iter + 1,count))), makeChoiceListfromCardList(cardChoices), type = 'button')
         chosenCList.append(cardChoices[choice])
         cardList.remove(cardChoices[choice])
   else: chosenCList = cardList
   if debugVerbosity >= 2: notify("### chosenCList: {}".format(chosenCList))
   for c in chosenCList:
      if destination == table: placeCard(c)
      else: c.moveTo(destination)
   if source != targetPL.piles['Discard Pile']:
      if debugVerbosity >= 2: notify("### Turning Pile Face Down")
      for c in source: c.isFaceUp = False # We hide again the source pile cards.
      cover.moveTo(me.ScriptingPile) # we cannot delete cards so we just hide it.
   if debugVerbosity >= 2: notify("### About to announce.")
   if len(chosenCList) == 0: announceString = "{} attempts to {} a card {}, but there were no valid targets.".format(announceText, destiVerb, sourcePath)
   else: announceString = "{} {} {} {}.".format(announceText, destiVerb, [c.name for c in chosenCList], sourcePath)
   if notification and multiplier > 0: notify(':> {}.'.format(announceString))
   if debugVerbosity >= 3: notify("<<< RetrieveX()")
   return announceString
   
def UseCustomAbility(Autoscript, announceText, card, targetCards = None, notification = None, n = 0): # not used yet.
   announceString = announceText 
   return announceString

def CustomScript(card, action = 'PLAY'): # Scripts that are complex and fairly unique to specific cards, not worth making a whole generic function for them.
   if debugVerbosity >= 1: notify(">>> CustomScript() with action: {}".format(action)) #Debug
   mute()
   global opponent
   discardPile = me.piles['Discard Pile']
   objectives = me.piles['Objective Deck']
   deck = me.piles['Command Deck']
   if card.name == 'A Journey to Dagobah' and action == 'THWART' and card.owner == me:
      if debugVerbosity >= 2: notify("### Journey to Dagobath Script")
      objList = []
      if debugVerbosity >= 2: notify("### Moving objectives to removed from game pile")
      for c in objectives:
         c.moveTo(me.ScriptingPile)
         objList.append(c._id)
      rnd(1,10)
      objNames = []
      objDetails = []
      if debugVerbosity >= 2: notify("### Storing objective properties and moving them back")
      for obj in objList:
         if debugVerbosity >= 3: notify("#### Card Name: {}".format(Card(obj).name))
         if Card(obj).name in objNames: 
            objList.remove(obj)
         else: 
            objNames.append(Card(obj).name)
            objDetails.append((Card(obj).Resources,Card(obj).properties['Damage Capacity'], Card(obj).Text)) # Creating a tuple with some details per objective
         Card(obj).moveTo(objectives)
      objChoices = []
      for iter in range(len(objList)):
         objChoices.append("{}\
                          \nResources {}, Damage Capacity: {}\
                          \nText: {}\
                          ".format(objNames[iter], objDetails[iter][0], objDetails[iter][1], objDetails[iter][2]))
      choice = SingleChoice("Which objective do you want to put into play from your deck?", objChoices, type = 'button', default = 0,cancelButton = False)
      storeObjective(Card(objList[choice]))
      shuffle(objectives)
      if debugVerbosity >= 2: notify("#### About to announce")
      notify("{} uses the ability of {} to replace it with {}".format(me,card,Card(objList[choice])))
   elif card.name == 'Black Squadron Pilot' and action == 'PLAY':
      if len(findTarget('AutoTargeted-atFighter_and_Unit-byMe')) > 0 and confirm("This unit has an optional ability which allows it to be played as an enchantment on a fighter. Do so now?"):
         fighter = findTarget('AutoTargeted-atFighter_and_Unit-byMe-choose1')
         if len(fighter) == 0: return
         hostCards = eval(getGlobalVariable('Host Cards'))
         hostCards[card._id] = fighter[0]._id
         setGlobalVariable('Host Cards',str(hostCards))
         cardAttachementsNR = len([att_id for att_id in hostCards if hostCards[att_id] == fighter[0]._id])
         if debugVerbosity >= 2: notify("### About to move into position") #Debug
         x,y = fighter[0].position
         card.moveToTable(x, y - ((cwidth(card) / 4 * playerside) * cardAttachementsNR))
         card.sendToBack()
         TokensX('Put1isEnhancement-isSilent', '', card)
   elif card.name == 'Wedge Antilles' and action == 'PLAY':
      if len(findTarget('AutoTargeted-atFighter_or_Speeder-byMe')) > 0 and confirm("This unit has an optional ability which allows it to be played as an enchantment on a Fighter or Speeder. Do so now?"):
         fighter = findTarget('AutoTargeted-atFighter_or_Speeder-byMe-choose1')
         if len(fighter) == 0: return
         hostCards = eval(getGlobalVariable('Host Cards'))
         hostCards[card._id] = fighter[0]._id
         setGlobalVariable('Host Cards',str(hostCards))
         cardAttachementsNR = len([att_id for att_id in hostCards if hostCards[att_id] == fighter[0]._id])
         if debugVerbosity >= 2: notify("### About to move into position") #Debug
         x,y = fighter[0].position
         card.moveToTable(x, y - ((cwidth(card) / 4 * playerside) * cardAttachementsNR))
         card.sendToBack()
         TokensX('Put1isEnhancement-isSilent', '', card)
   elif card.name == 'Cruel Interrogations' and action == 'PLAY':
      #if not confirm("Do you wish to use Cruel Interrogations' Reaction?"): return
      while len(opponent.hand) == 0: 
         if not confirm("Your opponent has no cards in their hand.\n\nRetry?"): return
      turn = num(getGlobalVariable('Turn'))
      captureTarget = opponent.hand.random()
      capture(chosenObj = card, targetC = captureTarget)
   elif card.name == 'Rancor' and action == 'afterCardRefreshing' and card.controller == me:
      possibleTargets = [c for c in table if c.Type == 'Unit' and not re.search('Vehicle',c.Traits)]
      if len(possibleTargets) == 0: return 'ABORT' # Nothing to kill
      minCost = 10 
      currTargets = []
      for c in possibleTargets:
         if debugVerbosity >= 4: notify("### Checking {}".format(c))
         if num(c.Cost) < minCost:
            del currTargets[:]
            currTargets.append(c)
            minCost = num(c.Cost)
         elif num(c.Cost) == minCost: currTargets.append(c)
         else: pass
      if debugVerbosity >= 2: notify("### Finished currTargets") #Debug         
      if debugVerbosity >= 4 and len(currTargets) > 0: notify("### Minimum Cost Targets = {}".format([c.name for c in currTargets])) #Debug
      if len(currTargets) == 1: finalTarget = currTargets[0]
      else: 
         choice = SingleChoice("Choose one unit to be destroyed by the Rancor", makeChoiceListfromCardList(currTargets), type = 'button', default = 0)
         if choice == 'ABORT': 
            notify(":::NOTICE::: {} has skipped Rancor's effects this turn".format(me))
            return
         finalTarget = currTargets[choice]
      if debugVerbosity >= 2: notify("### finalTarget = {}".format(finalTarget)) #Debug
      discard(finalTarget,silent = True)
      if finalTarget == card: notify("{}'s Rancor destroys itself in its wild rampage".format(me))
      else: notify("{}'s Rancor rampages and destroys {}".format(me,finalTarget))
   elif card.name == 'Rescue Mission' and action == 'PLAY':
      currentTargets = findTarget('Targeted-isCaptured')
      if len(currentTargets) == 0: return
      targetC = currentTargets[0] # We always only have one target.
      targetC.isFaceUp = True
      loopChk(targetC,'Type')
      removeCapturedCard(targetC) 
      targetC.highlight = None
      if targetC.Type == 'Unit' and confirm("You have rescued {}. Do you want to put immediately into play?".format(targetC.name)): 
         placeCard(targetC)
         notify("{} has rescued {} and put them straight into action".format(me,targetC))
      else: 
         targetC.moveTo(targetC.owner.hand)
         notify("{} has rescued a card".format(me))
   elif card.name == 'Return of the Jedi' and action == 'PLAY':
      if debugVerbosity >= 2: notify("### Return of the Jedi")
      discardList = []
      if debugVerbosity >= 2: notify("### Moving Force Users to 'removed from game' pile from discard pile")
      for c in discardPile:
         c.moveTo(me.ScriptingPile)
         discardList.append(c._id)
      rnd(1,10)
      unitNames = []
      unitDetails = []
      ForceUserList = []
      if debugVerbosity >= 2: notify("### Storing unit properties and moving them back")
      for unit in discardList:
         if debugVerbosity >= 3: notify("#### Card Name: {}".format(Card(unit).name))
         if not Card(unit).name in unitNames and re.search(r'Force User',Card(unit).Traits):
            ForceUserList.append(unit)
            unitNames.append(Card(unit).name)
            unitDetails.append((Card(unit).properties['Damage Capacity'],Card(unit).Traits,parseCombatIcons(Card(unit).properties['Combat Icons']),Card(unit).Text)) # Creating a tuple with some details per objective
         if debugVerbosity >= 3: notify("#### Finished Storing. Moving back")
         Card(unit).moveTo(discardPile)
      if len(ForceUserList) == 0: 
         whisper("::ERROR::: There is no force user in your discard pile!")
         return
      elif len(ForceUserList) == 1:
         choice = 0
      else:
         unitChoices = []
         for iter in range(len(ForceUserList)):
            unitChoices.append("{}\
                             \nDamage Capacity: {}\
                             \nTraits {}\
                             \nIcons: {}\
                             \nText: {}\
                             ".format(unitNames[iter], unitDetails[iter][0], unitDetails[iter][1], unitDetails[iter][2],unitDetails[iter][3]))
         choice = SingleChoice("Which Force User unit do you want to put into play from your discard pile?", unitChoices, type = 'button', default = 0, cancelButton = False)
      placeCard(Card(ForceUserList[choice]))
      if debugVerbosity >= 2: notify("#### About to announce")
      notify("{} returns into play".format(Card(ForceUserList[choice])))
   elif card.name == 'Superlaser Engineer' and action == 'PLAY': 
      cardList = []
      sendToBottomList = []
      iter = 0
      for c in deck.top(5):
         c.moveToTable((cwidth(c) * 2) - (iter * cwidth(c)),0)
         cardList.append(c._id)
         c.highlight = DummyColor
         iter += 1
      rnd(1,10)
      revealedCards = ''
      for cid in cardList: revealedCards += '{}, '.format(Card(cid))
      notify("{} activates the ability of their Superlaser Engineer and reveals the top 5 cards of their deck: {}".format(me,revealedCards))
      rnd(1,10)      
      for cid in cardList:
         if (Card(cid).Type == 'Event' or Card(cid).Type == 'Enhancement') and Card(cid).Affiliation == 'Imperial Navy' and num(Card(cid).Cost) >= 3:
            notify(":> {} moves {} to their hand".format(me,Card(cid)))
            Card(cid).moveTo(me.hand)
         else:
            sendToBottomList.append(Card(cid))
      sendToBottom(sendToBottomList)
   elif card.name == 'Take Them Prisoner' and action == 'PLAY': 
      debugNotify("Enterring 'Take Them Prisoner' Automation",1)
      turn = num(getGlobalVariable('Turn'))
      cardList = []
      cardNames = []
      cardDetails = []
      debugNotify("About to move cards to me.ScriptingPile",2)
      for c in opponent.piles['Command Deck'].top(3):
         c.moveTo(me.ScriptingPile)
         cardList.append(c._id)
      rnd(1,10)
      for cid in cardList:
         if debugVerbosity >= 3: notify("#### Card Name: {}".format(Card(cid).name))
         cardNames.append(Card(cid).name)
         cardDetails.append((Card(cid).Type,Card(cid).properties['Damage Capacity'],Card(cid).Resources,Card(cid).Traits,parseCombatIcons(Card(cid).properties['Combat Icons']),Card(cid).Text)) # Creating a tuple with some details per objective
         if debugVerbosity >= 3: notify("#### Finished Storing.")
      ChoiceTXT = []
      for iter in range(len(cardList)):
         ChoiceTXT.append("{}\
                          \nType: {}\
                          \nDamage Capacity: {}, Resources: {}\
                          \nTraits: {}\
                          \nIcons: {}\
                          \nText: {}\
                          ".format(cardNames[iter], cardDetails[iter][0], cardDetails[iter][1], cardDetails[iter][2],cardDetails[iter][3],cardDetails[iter][4],cardDetails[iter][5]))
      choice = SingleChoice("Which card do you wish to capture?", ChoiceTXT, type = 'button', default = 0,cancelButton = False)
      capturedC = Card(cardList.pop(choice))
      capturedC.moveTo(opponent.piles['Command Deck']) # We move it back to the deck, so that the capture function can announce the correct location from which it was taken.
      if debugVerbosity >= 3: notify("#### About to capture.")
      capture(chosenObj = card,targetC = capturedC, silent = True)
      if debugVerbosity >= 3: notify("#### Removing choice text")
      ChoiceTXT.pop(choice) # We also remove the choice text entry at that point.
      choice = SingleChoice("Which card do you wish to leave on top of your opponent's command deck?", ChoiceTXT, type = 'button', default = 0,cancelButton = False)
      for iter in range(len(cardList)):
         if debugVerbosity >= 2: confirm("#### Moving {} (was at position {}. choice was {})".format(Card(cardList[iter]).name, iter,choice))
         if iter == choice: Card(cardList[iter]).moveTo(opponent.piles['Command Deck'],0)
         else: Card(cardList[iter]).moveTo(opponent.piles['Command Deck'],1)
      notify(":> {} activates Takes Them Prisoner to capture one card from the top 3 cards of {}'s command deck".format(me,opponent))
   elif card.name == 'Trench Run' and action == 'PLAY': # We move this card to the opponent's exile in order to try and give control to them automatically.
      card.moveTo(opponent.ScriptingPile)
      rnd(1,10)
      if me.hasInvertedTable(): card.moveToTable(0,0)
      else:  card.moveToTable(0,-cheight(card))
      if debugVerbosity >= 2: notify("About to whisper") # Debug
      whisper(":::IMPORTANT::: Please make sure that the controller for this card is always the Dark Side player")
   elif card.name == 'Twist of Fate' and action == 'RESOLVEFATE': 
      for card in table:
         if card.highlight == EdgeColor or card.highlight == FateColor:
            card.moveTo(card.owner.piles['Discard Pile'])
      notify(":> {} discards all edge cards and restarts the edge battle".format(card))
   elif card.name == "Vader's TIE Advanced" and action == 'STRIKE':
      delayed_whisper("-- Calculating Vader's TIE Advanced Combat Icons. Please wait...")
      TokensX('Remove999Vaders TIE Advance:UD-isSilent', '', card)
      TokensX('Remove999Vaders TIE Advance:BD-isSilent', '', card)
      TokensX('Remove999Vaders TIE Advance:Tactics-isSilent', '', card)
      if not confirm("Do you want to use Vader's TIE Advanced reaction?"): return
      disCard = deck.top()
      disCard.moveTo(discardPile)
      rnd(1,10)
      Unit_Damage, Blast_Damage, Tactics = calculateCombatIcons(card = disCard)
      if Unit_Damage: TokensX('Put{}Vaders TIE Advance:UD-isSilent'.format(Unit_Damage), '', card)
      if Blast_Damage: TokensX('Put{}Vaders TIE Advance:BD-isSilent'.format(Blast_Damage), '', card)
      if Tactics: TokensX('Put{}Vaders TIE Advance:Tactics-isSilent'.format(Tactics), '', card)
      if Unit_Damage or Blast_Damage or Tactics:
         notify("{} discards {} and Vader's TIE Advanced strike is boosted by {}".format(me,disCard,parseCombatIcons(disCard.properties['Combat Icons'])))
      else: 
         notify("{} discards {} and Vader's TIE Advanced strike is not boosted".format(me,disCard,parseCombatIcons(disCard.properties['Combat Icons'])))
   elif (card.name == "Yoda" or card.name == "Rogue Three") and action == 'STRIKE':
      delayed_whisper("-- Calculating Extra Combat Icons from enhancements. Please wait...")
      TokensX('Remove999Enhancement Bonus:UD-isSilent', '', card)
      TokensX('Remove999Enhancement Bonus:BD-isSilent', '', card)
      hostCards = eval(getGlobalVariable('Host Cards'))
      cardAttachementsNR = len([att_id for att_id in hostCards if hostCards[att_id] == card._id])
      if cardAttachementsNR and gotEdge():
         TokensX('Put{}Enhancement Bonus:UD-isSilent'.format(cardAttachementsNR), '', card)
         TokensX('Put{}Enhancement Bonus:BD-isSilent'.format(cardAttachementsNR), '', card)
   elif card.name == "Secret Informant" and action == 'USE':
      if card.orientation != Rot90:
         whisper(":::ERROR::: Secret Informant must be participating in the engagement to use her ability")
         return
      if len([c for c in table if c.highlight == FateColor and c.Type == 'Fate' and c.owner == me]) and not confirm("You are supposed to use this effect once you're already used all your fate cards on the table (i.e. they all should have a silver highlight now)\
                  \n\nHave you done this already?"): return
      for c in table:
         if c.highlight == EdgeColor and c.Type == 'Fate' and c.owner == me:
            c.highlight = FateColor
      notify("{}'s secret informant allows them to resolve all their fate cards an extra time this battle".format(me))
   elif card.name == "The Secret of Yavin 4" and action == 'USE':
      EngagedObjective = getGlobalVariable('Engaged Objective')
      if EngagedObjective == 'None': 
         whisper(":::Error::: No Engagement Currently ongoing")
         return
      else:
         currentTarget = Card(num(EngagedObjective))     
         if currentTarget.controller != me or currentTarget == card:
            whisper(":::Error::: Current engagement not at another on of your objectives.")
            return
      currentTarget.highlight = None
      card.highlight = DefendColor
      setGlobalVariable('Engaged Objective',str(card._id))
      notify("{} activates {} and moves the engagement to it".format(me,card))
   elif card.name == "Echo Caverns" and action == 'USE':
      if (card.markers[mdict['Focus']]
            and card.markers[mdict['Focus']] >= 1
            and not confirm("Card is already exhausted. Bypass?")):
         return 
      currentTargets = findTarget('Targeted-atUnit')
      if len(currentTargets) != 2:
         delayed_whisper(":::ERROR::: You must target exactly 2 units to use this ability")
         return
      cardATraits = currentTargets[0].Traits.split('-')
      cardBTraits = currentTargets[1].Traits.split('-')
      commonTrait = False
      for TraitA in cardATraits:
         if TraitA == 'Unique': continue # "Unique" is not an actual trait.
         if TraitA in cardBTraits: commonTrait = True
      if not commonTrait: 
         delayed_whisper(":::ERROR::: The two target units must share a common Trait.")
         return
      targetChoices = makeChoiceListfromCardList(currentTargets)
      choiceC = SingleChoice("Choose from which card to remove a combat icon", targetChoices, type = 'button', default = 0)
      if choiceC == 'ABORT': return
      if debugVerbosity >= 4: notify("### choiceC = {}".format(choiceC)) # Debug
      if debugVerbosity >= 4: notify("### currentTargets = {}".format([currentTarget.name for currentTarget in currentTargets])) # Debug
      sourceCard = currentTargets.pop(choiceC)
      if debugVerbosity >= 2: notify("### sourceCard = {}".format(sourceCard)) # Debug
      targetCard = currentTargets[0] # After we pop() the choice card, whatever remains is the target card.
      if debugVerbosity >= 2: notify("### targetCard = {}".format(targetCard)) # Debug
      printedIcons = parseCombatIcons(sourceCard.properties['Combat Icons'])
      IconChoiceList = ["Unit Damage","Edge-Enabled Unit Damage","Blast Damage","Edge-Enabled Blast Damage","Tactics","Edge-Enabled Tactics"] # This list is a human readable one for the user to choose an icon
      IconList = ["UD","EE-UD","BD","EE-BD","Tactics","EE-Tactics"] # This list has the same icons as the above, but uses the keywords that the game expects in a marker, so it makes it easier to figure out which icon the user selected.
      if debugVerbosity >= 2: notify("### About to select combat icon to steal")
      choiceIcons = SingleChoice("The card has the following printed Combat Icons: {}.\nChoose a combat icon to steal.\n(We leave the choice open, in case the card has received a combat icon from a card effect)".format(printedIcons), IconChoiceList, type = 'button', default = 0)
      #card.markers[mdict['Focus']] += 1
      addMarker(card, 'Focus',1, True)
      TokensX('Put1Echo Caverns:minus{}-isSilent'.format(IconList[choiceIcons]), '', sourceCard)
      TokensX('Put1Echo Caverns:{}-isSilent'.format(IconList[choiceIcons]), '', targetCard)
      notify("{} activates {} to move one {} icon from {} to {}".format(me,card,IconChoiceList[choiceIcons],sourceCard,targetCard))
   elif card.name == "Prophet of the Dark Side" and action == 'PLAY':
         cardView = me.piles['Command Deck'][1]
         ScriptingPile
         cardView.moveTo(me.ScriptingPile)
         #cardView.isFaceUp = True
         rnd(1,10)
         if not haveForce():
            delayed_whisper(":> The Prophet foresees that {} is upcoming!".format(cardView)) # If the player doesn't have the force, we just announce the card
         else: # If the player has the force, he has a chance to draw the card in their hand.
            StackTop = [cardView]
            cardDetails = makeChoiceListfromCardList(StackTop, True)
            if confirm("The Prophet Foresees:\n{}\n\nDo you want to draw this card".format(cardDetails[0])):
               cardView.moveTo(me.hand)
               notify("The Prophet of the Dark Side has drawn 1 card for {}".format(me))
         if cardView.group == me.ScriptingPile: cardView.moveTo(me.piles['Command Deck'])
         rnd(1,10)
   elif card.name == "Z-95 Headhunter" and action == 'STRIKE':
      opponent = findOpponent()
      shownCards = showatrandom(targetPL = opponent, silent = True)
      if len(shownCards) == 0:
         notify("{} has no cards in their hand".format(opponent))
         return
      notify("{} discovers {} in an surprise strike!".format(card,shownCards[0]))
      rnd(1,10)
      if fetchProperty(shownCards[0], 'Type') == 'Unit': 
         capture(targetC = shownCards[0], silent = True)
         notify("{} has captured a unit.".format(card))
      else: shownCards[0].moveTo(shownCards[0].owner.hand)
      rnd(1,10)
   elif card.name == "Last Defense of Hoth" and action == 'USE':
      if oncePerTurn(card, silent = True, act = 'manual') == 'ABORT': return
      if confirm("Do you want to use Last Defence of Hoth's special ability?"):
         topCard = me.piles['Command Deck'].top()
         if playEdge(topCard,True) != 'ABORT':
            notify("{} used {} to play an edge card from the top of their command deck".format(me,card))
   else: notify("{} uses {}'s ability".format(me,card)) # Just a catch-all.
#------------------------------------------------------------------------------
# Helper Functions
#------------------------------------------------------------------------------
       
def findTarget(Autoscript, fromHand = False, card = None): # Function for finding the target of an autoscript
   debugNotify(">>> findTarget(){}".format(extraASDebug(Autoscript))) #Debug
   debugNotify("fromHand = {}. card = {}".format(fromHand,card)) #Debug
   global reversePlayerChk, Stored_Attachments
   try:
      if fromHand == True or re.search(r'-fromHand',Autoscript): group = me.hand
      elif re.search(r'-fromTopDeckMine',Autoscript): # Quick job because I cannot be bollocksed.
         debugNotify("Returing my top deck card",2)
         return [me.piles['Deck'].top()]
      elif re.search(r'-fromTopDeckOpponents',Autoscript): 
         debugNotify("Returing opponent top deck card",2)
         opponent = findOpponent()
         return [opponent.piles['Deck'].top()]
      else: group = table
      foundTargets = []
      if re.search(r'Targeted', Autoscript):
         requiredAllegiances = []
         targetGroups = prepareRestrictions(Autoscript)
         if debugVerbosity >= 2: notify("### About to start checking all targeted cards.\n### targetGroups:{}".format(targetGroups)) #Debug
         for targetLookup in group: # Now that we have our list of restrictions, we go through each targeted card on the table to check if it matches.
            if ((targetLookup.targetedBy and targetLookup.targetedBy == me) or re.search(r'AutoTargeted', Autoscript)) and targetLookup.highlight != EdgeColor and targetLookup.highlight !=FateColor: 
            # OK the above target check might need some decoding:
            # Look through all the cards on the group and start checking only IF...
            # * Card is targeted and targeted by the player OR target search has the -AutoTargeted modulator and it is NOT highlighted as a Fate, Edge or Captured.
            # * The player who controls this card is supposed to be me or the enemy.
               if debugVerbosity >= 2: notify("### Checking {}".format(targetLookup))
               if card:
                  if card.controller != me: # If we have provided the originator card to findTarget, and the card is not our, we assume that we need to treat the script as being run by our opponent
                     debugNotify("Reversing player check")
                     reversePlayerChk = True
               if not checkSpecialRestrictions(Autoscript,targetLookup): continue
               reversePlayerChk = False # We return things to normal now.
               if re.search(r'-onHost',Autoscript):   
                  if debugVerbosity >= 2: notify("### Looking for Host")
                  if not card: continue # If this targeting script targets only a host and we have not passed what the attachment is, we cannot find the host, so we abort.
                  if debugVerbosity >= 2: notify("### Attachment is: {}".format(card))
                  # hostCards = eval(getGlobalVariable('Host Cards'))
                  isHost = False
                  for attachment in Stored_Attachments:
                     if attachment == card._id and StoredAttachment[attachment] == targetLookup._id: 
                        if debugVerbosity >= 2: notify("### Host found! {}".format(targetLookup))
                        isHost = True
                  if not isHost: continue
               #if re.search(r'-isJailer',Autoscript): # With this modulator, we're trying to target only cards which are captured by a specific objective
                  #if debugVerbosity >= 2: notify("### Looking for Captured Cards")
                  #if not card: continue # If this targeting script targets only a captured card's Jailer and we have not passed what the attachment is, we cannot find the Jailer, so we abort.
                  #if debugVerbosity >= 2: notify("### Captured Card is: {}".format(card))
                  #capturedCards = eval(getGlobalVariable('Captured Cards'))
                  #isJailer = False
                  #for capturedC in capturedCards:
                     #if capturedCards[capturedC] == card._id and capturedC == targetLookup._id: 
                        #if debugVerbosity >= 2: notify("### Captured Card found! {}".format(targetLookup))
                        #isJailer = True
                  #if not isJailer: continue
               if checkCardRestrictions(gatherCardProperties(targetLookup), targetGroups): 
                  if not targetLookup in foundTargets: 
                     if debugVerbosity >= 3: notify("### About to append {}".format(targetLookup)) #Debug
                     foundTargets.append(targetLookup) # I don't know why but the first match is always processed twice by the for loop.
               elif debugVerbosity >= 3: notify("### findTarget() Rejected {}".format(targetLookup))# Debug
         if debugVerbosity >= 2: notify("### Finished seeking. foundTargets List = {}".format([c.name for c in foundTargets]))
         if re.search(r'DemiAutoTargeted', Autoscript):
            if debugVerbosity >= 2: notify("### Checking DemiAutoTargeted switches")# Debug
            targetNRregex = re.search(r'-choose([1-9])',Autoscript)
            targetedCards = 0
            foundTargetsTargeted = []
            if debugVerbosity >= 2: notify("### About to count targeted cards")# Debug
            for targetC in foundTargets:
               if targetC.targetedBy and targetC.targetedBy == me: foundTargetsTargeted.append(targetC)
            if targetNRregex:
               if debugVerbosity >= 2: notify("!!! targetNRregex exists")# Debug
               if num(targetNRregex.group(1)) > len(foundTargetsTargeted): pass # Not implemented yet. Once I have choose2 etc I'll work on this
               else: # If we have the same amount of cards targeted as the amount we need, then we just select the targeted cards
                  foundTargets = foundTargetsTargeted # This will also work if the player has targeted more cards than they need. The later choice will be simply between those cards.
            else: # If we do not want to choose, then it's probably a bad script. In any case we make sure that the player has targeted something (as the alternative it giving them a random choice of the valid targets)
               del foundTargets[:]
         if len(foundTargets) == 0 and not re.search(r'(?<!Demi)AutoTargeted', Autoscript) and not re.search(r'noTargetingError', Autoscript): 
            targetsText = ''
            mergedList = []
            for posRestrictions in targetGroups: 
               if debugVerbosity >= 2: notify("### About to notify on restrictions")# Debug
               if targetsText == '': targetsText = '\nYou need: '
               else: targetsText += ', or '
               del mergedList[:]
               mergedList += posRestrictions[0]
               if len(mergedList) > 0: targetsText += "{} and ".format(mergedList)  
               del mergedList[:]
               mergedList += posRestrictions[1]
               if len(mergedList) > 0: targetsText += "not {}".format(mergedList)
               if targetsText.endswith(' and '): targetsText = targetsText[:-len(' and ')]
            if debugVerbosity >= 2: notify("### About to chkPlayer()")# Debug
            if card:
               if card.controller != me: # If we have provided the originator card to findTarget, and the card is not our, we assume that we need to treat the script as being run by our opponent
                  debugNotify("Reversing player check")
                  reversePlayerChk = True
            if not chkPlayer(Autoscript, targetLookup.controller, False, True): 
               allegiance = re.search(r'target(Opponents|Mine)', Autoscript)
               requiredAllegiances.append(allegiance.group(1))
            reversePlayerChk = False # We return things to normal now.
            if len(requiredAllegiances) > 0: targetsText += "\nValid Target Allegiance: {}.".format(requiredAllegiances)
            delayed_whisper(":::ERROR::: You need to target a valid card before using this action{}.".format(targetsText))
         elif len(foundTargets) >= 1 and re.search(r'-choose',Autoscript):
            if debugVerbosity >= 2: notify("### Going for a choice menu")# Debug
            choiceType = re.search(r'-choose([0-9]+)',Autoscript)
            targetChoices = makeChoiceListfromCardList(foundTargets)
            if not card: choiceTitle = "Choose one of the valid targets for this effect"
            else: choiceTitle = "Choose one of the valid targets for {}'s ability".format(card.name)
            if debugVerbosity >= 2: notify("### Checking for SingleChoice")# Debug
            if choiceType.group(1) == '1':
               if len(foundTargets) == 1: choice = 0 # If we only have one valid target, autoselect it.
               else: choice = SingleChoice(choiceTitle, targetChoices, type = 'button', default = 0)
               if choice == 'ABORT': del foundTargets[:]
               else: foundTargets = [foundTargets.pop(choice)] # if we select the target we want, we make our list only hold that target
      if debugVerbosity >= 3: # Debug
         tlist = [] 
         for foundTarget in foundTargets: tlist.append(foundTarget.name) # Debug
         notify("<<< findTarget() by returning: {}".format(tlist))
      return foundTargets
   except: notify("!!!ERROR!!! on findTarget()")

def gatherCardProperties(card):
   if debugVerbosity >= 1: notify(">>> gatherCardProperties()") #Debug
   cardProperties = []
   if debugVerbosity >= 4: notify("### Appending name") #Debug                
   cardProperties.append(card.name) # We are going to check its name
   if debugVerbosity >= 4: notify("### Appending Type") #Debug                
   cardProperties.append(card.Type) # We are going to check its Type
   if debugVerbosity >= 4: notify("### Appending Faction") #Debug                
   cardProperties.append(card.Faction) # We are going to check its Affiliation
   if debugVerbosity >= 4: notify("### Appending Subtypes") #Debug                
   cardSubtypes = card.Subtypes.split('.') 
   for cardSubtype in cardSubtypes:
      strippedCS = cardSubtype.strip() # Remove any leading/trailing spaces between traits. We need to use a new variable, because we can't modify the loop iterator.
      if strippedCS: cardProperties.append(strippedCS) # If there's anything left after the stip (i.e. it's not an empty string anymrore) add it to the list.
   if debugVerbosity >= 4: notify("### Appending Keywords") #Debug                
   cardKeywords = card.Keyword.split('.') 
   for cardKeyword in cardKeywords:
      strippedCS = cardKeyword.strip() # Remove any leading/trailing spaces between traits. We need to use a new variable, because we can't modify the loop iterator.
      if strippedCS: cardProperties.append(strippedCS) # If there's anything left after the stip (i.e. it's not an empty string anymrore) add it to the list.
   if debugVerbosity >= 3: notify("<<< gatherCardProperties() with Card Properties: {}".format(cardProperties)) #Debug
   return cardProperties

def prepareRestrictions(Autoscript, seek = 'target'):
# This is a function that takes an autoscript and attempts to find restrictions on card traits/types/names etc. 
# It goes looks for a specific working and then gathers all restrictions into a list of tuples, where each tuple has a negative and a positive entry
# The positive entry (position [0] in the tuple) contains what card properties a card needs to have to be a valid selection
# The negative entry (position [1] in the tuple) contains what card properties a card needs to NOT have to be a vaid selection.
   if debugVerbosity >= 1: notify(">>> prepareRestrictions() {}. Seektype = {}".format(extraASDebug(Autoscript),seek)) #Debug
   validTargets = [] # a list that holds any type that a card must be, in order to be a valid target.
   targetGroups = []
   Autoscript = scrubTransferTargets(Autoscript)
   if seek == 'type': whatTarget = re.search(r'\b(type)([A-Za-z_{},& ]+)[-]?', Autoscript) # seek of "type" is used by autoscripting other players, and it's separated so that the same card can have two different triggers (e.g. see Darth Vader)
   elif seek == 'retrieve': whatTarget = re.search(r'\b(grab)([A-Za-z_{},& ]+)[-]?', Autoscript) # seek of "retrieve" is used when checking what types of cards to retrieve from one's deck or discard pile
   elif seek == 'reduce': whatTarget = re.search(r'\b(affects)([A-Za-z_{},& ]+)[-]?', Autoscript) # seek of "reduce" is used when checking for what types of cards to recuce the cost.
   else: whatTarget = re.search(r'\b(at)([A-Za-z_{},& ]+)[-]?', Autoscript) # We signify target restrictions keywords by starting a string with "or"
   if whatTarget: 
      if debugVerbosity >= 2: notify("### Splitting on _or_") #Debug
      validTargets = whatTarget.group(2).split('_or_') # If we have a list of valid targets, split them into a list, separated by the string "_or_". Usually this results in a list of 1 item.
      ValidTargetsSnapshot = list(validTargets) # We have to work on a snapshot, because we're going to be modifying the actual list as we iterate.
      for iter in range(len(ValidTargetsSnapshot)): # Now we go through each list item and see if it has more than one condition (Eg, non-desert fief)
         if debugVerbosity >= 2: notify("### Creating empty list tuple") #Debug            
         targetGroups.insert(iter,([],[])) # We create a tuple of two list. The first list is the valid properties, the second the invalid ones
         multiConditionTargets = ValidTargetsSnapshot[iter].split('_and_') # We put all the mutliple conditions in a new list, separating each element.
         if debugVerbosity >= 2: notify("###Splitting on _and_ & _or_ ") #Debug
         if debugVerbosity >= 4: notify("### multiConditionTargets is: {}".format(multiConditionTargets)) #Debug
         for chkCondition in multiConditionTargets:
            if debugVerbosity >= 4: notify("### Checking: {}".format(chkCondition)) #Debug
            regexCondition = re.search(r'(no[nt]){?([A-Za-z,& ]+)}?', chkCondition) # Do a search to see if in the multicondition targets there's one with "non" in front
            if regexCondition and (regexCondition.group(1) == 'non' or regexCondition.group(1) == 'not'):
               if debugVerbosity >= 4: notify("### Invalid Target") #Debug
               if regexCondition.group(2) not in targetGroups[iter][1]: targetGroups[iter][1].append(regexCondition.group(2)) # If there is, move it without the "non" into the invalidTargets list.
            else: 
               if debugVerbosity >= 4: notify("### Valid Target") #Debug
               targetGroups[iter][0].append(chkCondition) # Else just move the individual condition to the end if validTargets list
   elif debugVerbosity >= 2: notify("### No restrictions regex") #Debug 
   if debugVerbosity >= 3: notify("<<< prepareRestrictions() by returning: {}.".format(targetGroups))
   return targetGroups

def checkCardRestrictions(cardPropertyList, restrictionsList):
   if debugVerbosity >= 1: notify(">>> checkCardRestrictions()") #Debug
   if debugVerbosity >= 2: notify("### cardPropertyList = {}".format(cardPropertyList)) #Debug
   if debugVerbosity >= 2: notify("### restrictionsList = {}".format(restrictionsList)) #Debug
   validCard = True
   for restrictionsGroup in restrictionsList: 
   # We check each card's properties against each restrictions group of valid + invalid properties.
   # Each Restrictions group is a tuple of two lists. First list (tuple[0]) is the valid properties, and the second list is the invalid properties
   # We check if all the properties from the valid list are in the card properties
   # And then we check if no properties from the invalid list are in the properties
   # If both of these are true, then the card is a valid choice for our action.
      validCard = True # We need to set it here as well for further loops
      if debugVerbosity >= 3: notify("### restrictionsGroup checking: {}".format(restrictionsGroup))
      if len(restrictionsList) > 0 and len(restrictionsGroup[0]) > 0: 
         for validtargetCHK in restrictionsGroup[0]: # look if the card we're going through matches our valid target checks
            if debugVerbosity >= 4: notify("### Checking for valid match on {}".format(validtargetCHK)) #Debug
            if not validtargetCHK in cardPropertyList: 
               if debugVerbosity >= 4: notify("### {} not found in {}".format(validtargetCHK,cardPropertyList)) #Debug
               validCard = False
      elif debugVerbosity >= 4: notify("### No positive restrictions")
      if len(restrictionsList) > 0 and len(restrictionsGroup[1]) > 0: # If we have no target restrictions, any selected card will do as long as it's a valid target.
         for invalidtargetCHK in restrictionsGroup[1]:
            if debugVerbosity >= 4: notify("### Checking for invalid match on {}".format(invalidtargetCHK)) #Debug
            if invalidtargetCHK in cardPropertyList: validCard = False
      elif debugVerbosity >= 4: notify("### No negative restrictions")
      if validCard: break # If we already passed a restrictions check, we don't need to continue checking restrictions 
   if debugVerbosity >= 1: notify("<<< checkCardRestrictions() with return {}".format(validCard)) #Debug
   return validCard

def checkSpecialRestrictions(Autoscript,card):
# Check the autoscript for special restrictions of a valid card
# If the card does not validate all the restrictions included in the autoscript, we reject it
   if debugVerbosity >= 1: notify(">>> checkSpecialRestrictions() {}".format(extraASDebug(Autoscript))) #Debug
   if debugVerbosity >= 1: notify("### Card: {}".format(card)) #Debug
   validCard = True
   Autoscript = scrubTransferTargets(Autoscript)
   if re.search(r'isCurrentObjective',Autoscript) and card.highlight != DefendColor: 
      debugNotify("!!! Failing because it's not current objective", 2)
      validCard = False
   if re.search(r'isParticipating',Autoscript) and card.orientation != Rot90 and card.highlight != DefendColor: 
      debugNotify("!!! Failing because it's not participating", 2)
      validCard = False
   if re.search(r'isAlone',Autoscript): # If OrigAlone means that the originator of the scipt needs to be alone in the engagement.
      for c in table:
         if c != card and c.orientation == Rot90 and c.controller == card.controller: 
            debugNotify("!!! Failing because it's not participating alone", 2)
            validCard = False
   if re.search(r'isCaptured',Autoscript):
      if card.highlight != CapturedColor: 
         debugNotify("!!! Failing because we werelooking for a captured card but this ain't it", 2)
         validCard = False
      elif re.search(r'isCapturedCurrentObjective',Autoscript):
         try:
            capturedCards = eval(getGlobalVariable('Captured Cards'))
            debugNotify("capturedCards = {}".format(capturedCards.get(card._id,None)))
            currentTarget = Card(num(getGlobalVariable('Engaged Objective')))
            debugNotify("currentTarget = {}".format(currentTarget))
            if capturedCards[card._id] != currentTarget._id:
               debugNotify("!!! Failing because we were looking for a captured card at the current objective but this isn't one", 2)
               validCard = False           
         except: 
            debugNotify("!!! Failing because we crashed while looking for isCapturedCurrentObjective. Not in conflict?", 2)
            validCard = False           
   if not re.search(r'isCaptured',Autoscript) and card.highlight == CapturedColor:
         debugNotify("Failing because the current target is captured but we're not targeting captured card explicitly.", 2)
         validCard = False      
   if re.search(r'hasCaptures',Autoscript):
      capturedCards = eval(getGlobalVariable('Captured Cards'))
      if card._id not in capturedCards.values():
         debugNotify("!!! Failing because we were looking for card that has captured other cards but this doesn't", 2)
         validCard = False
   if re.search(r'isUnpaid',Autoscript) and card.highlight != UnpaidColor: 
      debugNotify("!!! Failing because card is not Unpaid", 2)
      validCard = False
   if re.search(r'isReady',Autoscript) and card.highlight != UnpaidColor and card.highlight != ReadyEffectColor: 
      debugNotify("!!! Failing because card is not Paid", 2)
      validCard = False
   if re.search(r'isEdgeWinner',Autoscript):
      plAffiliation = getSpecial('Affiliation',card.controller)
      if not plAffiliation.markers[mdict['Edge']]:
         debugNotify("!!! Failing because card's controller is not the edge winner")
         validCard = False
   if re.search(r'isNotParticipating',Autoscript) and (card.orientation == Rot90 or card.highlight == DefendColor): 
      debugNotify("!!! Failing because unit is participating", 2)
      validCard = False
   if re.search(r'isAttacking',Autoscript) or re.search(r'isDefending',Autoscript):
      EngagedObjective = getGlobalVariable('Engaged Objective')
      if EngagedObjective == 'None': 
         debugNotify("!!! Failing because we're looking for at Attacker/Defender and there's no objective", 2)
         validCard = False
      else:
         currentTarget = Card(num(EngagedObjective))
         if re.search(r'isAttacking',Autoscript) and currentTarget.controller == card.controller:
            if len(players) == 1 and debugVerbosity >= 0: notify("!!! Bypassing not-attacking fail because we're debugging")
            else: 
               debugNotify("!!! Failing because unit it not attacking", 2)
               validCard = False
         elif re.search(r'isDefending',Autoscript) and currentTarget.controller != card.controller: 
            if len(players) == 1 and debugVerbosity >= 0: notify("!!! Bypassing not-defending fail because we're debugging")
            else: 
               debugNotify("!!! Failing because unit is not defending", 2)
               validCard = False
   if re.search(r'isDamagedObjective',Autoscript): # If this keyword is there, the current objective needs to be damaged
      debugNotify("Checking for Damaged Objective", 2)
      EngagedObjective = getGlobalVariable('Engaged Objective')
      if EngagedObjective == 'None': 
         debugNotify("!!! Failing because we're looking for a damaged objective and there's no objective at all", 2)         
         validCard = False
      else:
         currentTarget = Card(num(EngagedObjective))
         if not currentTarget.markers[mdict['Damage']]:
            try: debugNotify("Requires Damaged objective but {} Damage Markers found on {}".format(currentTarget.markers[mdict['Damage']],currentTarget),2)
            except: debugNotify("Oops! I guess markers were null", 2)
            validCard = False
   if re.search(r'isCommited',Autoscript) and card.highlight != LightForceColor and card.highlight != DarkForceColor: 
      debugNotify("!!! Failing because card is not committed to the force", 2)
      validCard = False
   if re.search(r'isNotCommited',Autoscript) and (card.highlight == LightForceColor or card.highlight == DarkForceColor): 
      debugNotify("!!! Failing because card is committed to the force", 2)
      validCard = False
   if re.search(r'ifhasEdge',Autoscript) and not gotEdge(card.controller): 
      if len(players) == 1 and debugVerbosity >= 0: notify("!!! Bypassing have-edge fail because we're debugging")
      else: 
         debugNotify("!!! Failing because card's controller does not have the edge", 2)
         validCard = False
   if re.search(r'ifhasntEdge',Autoscript) and gotEdge(card.controller): 
      if len(players) == 1 and debugVerbosity >= 0: notify("!!! Bypassing hasn't-edge fail because we're debugging")
      else: 
         debugNotify("!!! Failing because card's controller has the edge", 2)
         validCard = False
   if not chkPlayer(Autoscript, card.controller, False, True): 
      debugNotify("!!! Failing because not the right controller", 2)
      validCard = False
   markerName = re.search(r'-hasMarker{([\w :]+)}',Autoscript) # Checking if we need specific markers on the card.
   if markerName: #If we're looking for markers, then we go through each targeted card and check if it has any relevant markers
      if debugVerbosity >= 2: notify("### Checking marker restrictions")# Debug
      if debugVerbosity >= 2: notify("### Marker Name: {}".format(markerName.group(1)))# Debug
      if markerName.group(1) == 'AnyTokenType': #
         if not (card.markers[mdict['Focus']] or card.markers[mdict['Shield']] or card.markers[mdict['Damage']]): 
            debugNotify("!!! Failing because card is missing all default markers", 2)
            validCard = False
      else: 
         marker = findMarker(card, markerName.group(1))
         if not marker: 
            debugNotify("!!! Failing because it's missing marker", 2)
            validCard = False
   markerNeg = re.search(r'-hasntMarker{([\w ]+)}',Autoscript) # Checking if we need to not have specific markers on the card.
   if markerNeg: #If we're looking for markers, then we go through each targeted card and check if it has any relevant markers
      if debugVerbosity >= 2: notify("### Checking negative marker restrictions")# Debug
      if debugVerbosity >= 2: notify("### Marker Name: {}".format(markerNeg.group(1)))# Debug
      marker = findMarker(card, markerNeg.group(1))
      if marker: 
         debugNotify("!!! Failing because it has marker", 2)
         validCard = False
   elif debugVerbosity >= 4: notify("### No negative marker restrictions.")
   # Checking if the target needs to have a property at a certiain value. 
   propertyReq = re.search(r'-hasProperty{([\w ]+)}(eq|le|ge|gt|lt)([0-9])',Autoscript) 
   if propertyReq and validCard: validCard = compareValue(propertyReq.group(2), num(card.properties[propertyReq.group(1)]), num(propertyReq.group(3))) 
   # Since we're placing the value straight into validCard, we don't want to check at all is validCard is already false
   # Checking if the target needs to have a markers at a particular value.
   MarkerReq = re.search(r'-ifMarkers{([\w ]+)}(eq|le|ge|gt|lt)([0-9])',Autoscript)
   if MarkerReq and validCard: 
      if debugVerbosity >= 4: notify("Found marker comparison req. regex groups: {}".format(MarkerReq.groups()))
      markerSeek = findMarker(card, MarkerReq.group(1))
      if markerSeek:
         validCard = compareValue(MarkerReq.group(2), card.markers[markerSeek], num(MarkerReq.group(3)))
   # Checking if the DS Dial needs to be at a specific value
   DialReq = re.search(r'-ifDial(eq|le|ge|gt|lt)([0-9]+)',Autoscript)
   if DialReq and validCard: validCard = compareValue(DialReq.group(1), me.counters['Death Star Dial'].value, num(DialReq.group(2)))
   if debugVerbosity >= 1: notify("<<< checkSpecialRestrictions() with return {}".format(validCard)) #Debug
   return validCard

def checkOriginatorRestrictions(Autoscript,card):
# Check the autoscript for special restrictions on the originator of a specific effect. 
# If the card does not validate all the restrictions included in the autoscript, we reject it
# For example Darth Vader 41/2 requires that he is attacking before his effect takes place. In this case we'd check that he is currently attacking and return True is he is
   if debugVerbosity >= 1: notify(">>> checkOriginatorRestrictions() {}".format(extraASDebug(Autoscript))) #Debug
   if debugVerbosity >= 1: notify("### Card: {}".format(card)) #Debug
   validCard = True
   Autoscript = scrubTransferTargets(Autoscript)
   if re.search(r'ifOrigCurrentObjective',Autoscript):
      if re.search(r'-ifOrigCurrentObjectiveHost', Autoscript): # This submodulator fires only if the card being checked for scripts is currently hosted on the engaged objective.
         hostCards = eval(getGlobalVariable('Host Cards')) 
         currObjID = getGlobalVariable('Engaged Objective')
         if currObjID == 'None' or Card(num(currObjID)) != Card(hostCards[card._id]): 
            debugNotify("!!! Failing because originator card's host is not the current objective", 2)
            validCard = False
      elif card.highlight != DefendColor:
         debugNotify("!!! Failing because originator is not the current objective", 2)
         validCard = False
   if re.search(r'ifOrigCaptures',Autoscript):
      capturedCards = eval(getGlobalVariable('Captured Cards'))
      if card._id not in capturedCards.values(): validCard = False
   if re.search(r'ifOrigParticipating',Autoscript):
      if re.search(r'-ifOrigParticipatingHost', Autoscript): # This submodulator fires only if the card being checked for scripts is currently hosted on a participating card.
         hostCards = eval(getGlobalVariable('Host Cards'))        
         try: # We use a try because if the card being checked has bot been attached (say because some monkey moved it manually to the table), the script will crash
            origHost = Card(hostCards[card._id])
            if origHost.orientation != Rot90 and origHost.highlight != DefendColor: 
               debugNotify("!!! Failing because originator card's host is not participating", 2)
               validCard = False
         except:
               debugNotify("!!! Failing crash when checking if originator card's host is participating", 2)
               validCard = False
      elif card.orientation != Rot90 and card.highlight != DefendColor: validCard = False
   if re.search(r'ifOrigAlone',Autoscript): # If OrigAlone means that the originator of the scipt needs to be alone in the engagement.
      for c in table:
         if c != card and c.orientation == Rot90 and c.controller == card.controller: validCard = False
   if re.search(r'ifOrigNotParticipating',Autoscript) and (card.orientation == Rot90 or card.highlight == DefendColor): validCard = False
   if re.search(r'ifOrigEdgeWinner',Autoscript):
      plAffiliation = getSpecial('Affiliation',card.controller)
      if not plAffiliation.markers[mdict['Edge']]:
         debugNotify("!!! Failing because originator's controller is not the edge winner")
         validCard = False
   if re.search(r'ifOrigEdgeLoser',Autoscript):
      plAffiliation = getSpecial('Affiliation',card.controller)
      if plAffiliation.markers[mdict['Edge']]:
         debugNotify("!!! Failing because originator's controller the edge winner")
         validCard = False
   if re.search(r'ifOrigAttacking',Autoscript) or re.search(r'ifOrigDefending',Autoscript):
      EngagedObjective = getGlobalVariable('Engaged Objective')
      if EngagedObjective == 'None': validCard = False
      else:
         currentTarget = Card(num(EngagedObjective))
         if re.search(r'ifOrigAttacking',Autoscript) and currentTarget.controller == card.controller: 
            if len(players) == 1 and debugVerbosity >= 0: notify("!!! Bypassing not-attacking fail because we're debugging")
            else: validCard = False
         elif re.search(r'ifOrigDefending',Autoscript)  and currentTarget.controller != card.controller: 
            if len(players) == 1 and debugVerbosity >= 0: notify("!!! Bypassing not-defending fail because we're debugging")
            else: validCard = False
   if re.search(r'isDamagedObjective',Autoscript): # If this keyword is there, the current objective needs to be damaged
      debugNotify("Checking for Damaged Objective", 2)
      EngagedObjective = getGlobalVariable('Engaged Objective')
      if EngagedObjective == 'None': 
         debugNotify("!!! Failing because we're looking for a damaged objective and there's no objective at all", 2)         
         validCard = False
      else:
         currentTarget = Card(num(EngagedObjective))
         if not currentTarget.markers[mdict['Damage']]:
            try: debugNotify("Requires Damaged objective but {} Damage Markers found on {}".format(currentTarget.markers[mdict['Damage']],currentTarget),2)
            except: debugNotify("Oops! I guess markers were null", 2)
            validCard = False
   if re.search(r'ifOrigCommited',Autoscript) and card.highlight != LightForceColor and card.highlight != DarkForceColor: validCard = False
   if re.search(r'ifOrigNotCommited',Autoscript) and (card.highlight == LightForceColor or card.highlight == DarkForceColor): validCard = False
   if re.search(r'ifOrighasEdge',Autoscript) and not gotEdge(card.controller): 
      if len(players) == 1 and debugVerbosity >= 0: notify("!!! Bypassing have-edge fail because we're debugging")
      else: validCard = False
   if re.search(r'ifOrighasntEdge',Autoscript) and gotEdge(card.controller): 
      if len(players) == 1 and debugVerbosity >= 0: notify("!!! Bypassing hasn't-edge fail because we're debugging")
      else: validCard = False
   #if not chkPlayer(Autoscript, card.controller, False, False): validCard = False
   markerName = re.search(r'-ifOrigHasMarker{([\w :]+)}',Autoscript) # Checking if we need specific markers on the card.
   if markerName: #If we're looking for markers, then we go through each targeted card and check if it has any relevant markers
      if debugVerbosity >= 2: notify("### Checking marker restrictions")# Debug
      if debugVerbosity >= 2: notify("### Marker Name: {}".format(markerName.group(1)))# Debug
      marker = findMarker(card, markerName.group(1))
      if not marker: validCard = False
   markerNeg = re.search(r'-ifOrigHasntMarker{([\w ]+)}',Autoscript) # Checking if we need to not have specific markers on the card.
   if markerNeg: #If we're looking for markers, then we go through each targeted card and check if it has any relevant markers
      if debugVerbosity >= 2: notify("### Checking negative marker restrictions")# Debug
      if debugVerbosity >= 2: notify("### Marker Name: {}".format(markerNeg.group(1)))# Debug
      marker = findMarker(card, markerNeg.group(1))
      if marker: validCard = False
   elif debugVerbosity >= 4: notify("### No negative marker restrictions.")
   # Checking if the originator needs to have a property at a certiain value. 
   propertyReq = re.search(r'-ifOrigHasProperty{([\w ]+)}(eq|le|ge|gt|lt)([0-9])',Autoscript) 
   if propertyReq and validCard: validCard = compareValue(propertyReq.group(2), num(card.properties[propertyReq.group(1)]), num(propertyReq.group(3))) # We don't want to check if validCard is already False
   # Checking if the target needs to have a markers at a particular value.
   MarkerReq = re.search(r'-ifOrigmarkers{([\w ]+)}(eq|le|ge|gt|lt)([0-9])',Autoscript)
   if MarkerReq and validCard: validCard = compareValue(MarkerReq.group(2), card.markers.get(findMarker(card, MarkerReq.group(1)),0), num(MarkerReq.group(3)))
   # Checking if the DS Dial needs to be at a specific value
   DialReq = re.search(r'-ifDial(eq|le|ge|gt|lt)([0-9]+)',Autoscript)
   if DialReq and validCard: validCard = compareValue(DialReq.group(1), me.counters['Death Star Dial'].value, num(DialReq.group(2)))
   if debugVerbosity >= 1: notify("<<< checkOriginatorRestrictions() with return {}".format(validCard)) #Debug
   return validCard

def scrubTransferTargets(Autoscript): # This functions clears the targeting modulators used by source and destination cards of the Transfer core command
   debugNotify(">>> scrubTransferTargets() with Autoscript: {}".format(Autoscript))
   if re.search(r'Transfer[0-9]',Autoscript): # If we're using the Transfer core command, then we're going to have source and destination conditions which will mess checks. We need to remove them.
      debugNotify("We got Transfer core command",2)
      newASregex = re.search(r'(Transfer.*?)-source',Autoscript) # We search until '-source' which is where the Transfer modulator's targeting regex starts
      if newASregex: debugNotify('newASregex = {}'.format(newASregex.groups()),2)
      else: debugNotify("Script could not find newASregex. Will error",2)
      Autoscript = newASregex.group(1) # We keep only everything in the basic targetting
   debugNotify("<<< scrubTransferTargets() with return {}".format(Autoscript))
   return Autoscript

   
def compareValue(comparison, value, requirement):
   debugNotify(">>> compareValue()")
   if comparison == 'eq' and value != requirement: return False # 'eq' stands for "Equal to"
   if comparison == 'le' and value > requirement: return False # 'le' stands for "Less or Equal"
   if comparison == 'ge' and value < requirement: return False # 'ge' stands for "Greater or Equal"
   if comparison == 'lt' and value >= requirement: return False # 'lt' stands for "Less Than"
   if comparison == 'gt' and value <= requirement: return False # 'gt' stands for "Greater Than"
   debugNotify("<<< compareValue() with return True")
   return True # If none of the requirements fail, we return true
     
def makeChoiceListfromCardList(cardList,includeText = False):
# A function that returns a list of strings suitable for a choice menu, out of a list of cards
# Each member of the list includes a card's name, traits, resources, markers and, if applicable, combat icons
   global Stored_Attachments
   if debugVerbosity >= 1: notify(">>> makeChoiceListfromCardList()")
   targetChoices = []
   if debugVerbosity >= 2: notify("### About to prepare choices list.")# Debug
   for T in cardList:
      if debugVerbosity >= 4: notify("### Checking {}".format(T))# Debug
      markers = 'Counters:'
      if T.markers[mdict['Wound']] and T.markers[mdict['Wound']] >= 1: markers += " {} Damage,".format(T.markers[mdict['Damage']])
      if T.markers[mdict['Success']] and T.markers[mdict['Success']] >= 1: markers += " {} Focus,".format(T.markers[mdict['Focus']])
      if markers != 'Counters:': markers += '\n'
      else: markers = ''
      if debugVerbosity >= 4: notify("### Finished Adding Markers. Adding stats...")# Debug               
      stats = ''
      if num(T.Skill) >= 1: stats += "Skill: {}. ".format(T.Skill)
      #if num(T.properties['Damage Capacity']) >= 1: stats += "HP: {}.".format(T.properties['Damage Capacity'])
      if T.Type == 'Character': combatIcons = "\nIcons: " + parseIcons(T.Icons)
      else: combatIcons = ''
      attachmentsList = [Card(cID).name for cID in getAttachments(T)]
      if len(attachmentsList) >= 1: cAttachments = '\nAttachments:' + str(attachmentsList)
      else: cAttachments = ''
      if debugVerbosity >= 4: notify("### Finished Adding Stats. Going to choice...")# Debug               
      choiceTXT = "{}\n{}\n{}{}{}{}".format(T.name,T.Type,markers,stats,combatIcons,cAttachments)
      targetChoices.append(choiceTXT)
   return targetChoices
   if debugVerbosity >= 3: notify("<<< makeChoiceListfromCardList()")

   
def chkPlayer(Autoscript, controller, manual, targetChk = False, player = me): # Function for figuring out if an autoscript is supposed to target an opponent's cards or ours.
# Function returns 1 if the card is not only for rivals, or if it is for rivals and the card being activated it not ours.
# This is then multiplied by the multiplier, which means that if the card activated only works for Rival's cards, our cards will have a 0 gain.
# This will probably make no sense when I read it in 10 years...
   debugNotify(">>> chkPlayer(). Controller is: {}".format(controller)) #Debug
   debugNotify("Autoscript = {}".format(Autoscript),3)
   try:
      validPlayer = 1 # We always succeed unless a check fails
      if targetChk: # If set to true, it means we're checking from the findTarget() function, which needs a different keyword in case we end up with two checks on a card's controller on the same script (e.g. Darth Vader)
         debugNotify("Doing targetChk",3)
         byOpponent = re.search(r'targetOpponents', Autoscript)
         byMe = re.search(r'targetMine', Autoscript)
      else:
         debugNotify("Doing normal chk",3)
         byOpponent = re.search(r'(byOpponent|forOpponent)', Autoscript)
         byMe = re.search(r'(byMe|forMe)', Autoscript)
      if re.search(r'duringOpponentTurn', Autoscript) and controller.isActivePlayer: 
         debugNotify("!!! Failing because ability is for {} opponent's turn and {}.isActivePlayer is {}".format(controller,controller,controller.isActivePlayer))            
         validPlayer = 0 # If the card can only fire furing its controller's opponent's turn
      elif re.search(r'duringMyTurn', Autoscript) and not controller.isActivePlayer: 
         debugNotify("!!! Failing because ability is for {}'s turn and {}.isActivePlayer is {}".format(controller,controller,controller.isActivePlayer))            
         validPlayer = 0 # If the card can only fire furing its controller's turn
      elif byOpponent and controller == player: 
         debugNotify("!!! Failing because ability is byOpponent and controller is {}".format(controller))
         validPlayer =  0 # If the card needs to be played by a rival.
      elif byMe and controller != player: 
         debugNotify("!!! Failing because ability is for byMe and controller is {}".format(controller))
         validPlayer =  0 # If the card needs to be played by us.
      else: debugNotify("!!! Succeeding by Default") # Debug
      if manual or len(players) == 1: 
         debugNotify("!!! Force Succeeding for Manual/Debug")         
         validPlayer = 1 # On a manual or debug run we always succeed
      if not reversePlayerChk: 
         debugNotify("<<< chkPlayer() with validPlayer: {}".format(validPlayer)) # Debug
         return validPlayer
      else: # In case reversePlayerChk is set to true, we want to return the opposite result. This means that if a scripts expect the one running the effect to be the player, we'll return 1 only if the one running the effect is the opponent. See Decoy at Dantoine for a reason
         debugNotify("<<< chkPlayer() reversed!") # Debug      
         if validPlayer == 0 or len(players) == 1 or manual or (not byOpponent and not byMe): return 1 # For debug purposes, I want it to be true when there's  only one player in the match
         else: return 0
   except: 
      notify("!!!ERROR!!! Null value on chkPlayer()")
      return 0

def chkWarn(card, Autoscript): # Function for checking that an autoscript announces a warning to the player
   if debugVerbosity >= 1: notify(">>> chkWarn(){}".format(extraASDebug(Autoscript))) #Debug
   global AfterRunInf, AfterTraceInf
   warning = re.search(r'warn([A-Z][A-Za-z0-9 ]+)-?', Autoscript)
   if warning:
      if warning.group(1) == 'Discard': 
         if not confirm("This action requires that you discard some cards. Have you done this already?"):
            whisper(":> Aborting action. Please discard the necessary amount of cards and run this action again")
            return 'ABORT'
      if warning.group(1) == 'ReshuffleOpponent': 
         if not confirm("This action will reshuffle your opponent's pile(s). Are you sure?\n\n[Important: Please ask your opponent not to take any clicks with their piles until this clicks is complete or the game might crash]"):
            whisper(":> Aborting action.")
            return 'ABORT'
      if warning.group(1) == 'GiveToOpponent': confirm('This card has an effect which if meant for your opponent. Please use the menu option "pass control to" to give them control.')
      if warning.group(1) == 'Reshuffle': 
         if not confirm("This action will reshuffle your piles. Are you sure?"):
            whisper(":> Aborting action.")
            return 'ABORT'
      if warning.group(1) == 'Workaround':
         notify(":::Note:::{} is using a workaround autoscript".format(me))
      if warning.group(1) == 'LotsofStuff': 
         if not confirm("This card modify the cards on the table significantly and very difficult to undo. Are you ready to proceed?"):
            whisper(":> Aborting action.")
            return 'ABORT'
   if debugVerbosity >= 3: notify("<<< chkWarn() gracefully") 
   return 'OK'

def per(Autoscript, card = None, count = 0, targetCards = None, notification = None): # This function goes through the autoscript and looks for the words "per<Something>". Then figures out what the card multiplies its effect with, and returns the appropriate multiplier.
   if debugVerbosity >= 1: notify(">>> per(){}".format(extraASDebug(Autoscript))) #Debug
   if targetCards is None: targetCards = []
   div = 1
   ignore = 0
   max = 0 # A maximum of 0 means no limit
   per = re.search(r'\b(per|upto)(Target|Host|Every)?([A-Z][^-]*)-?', Autoscript) # We're searching for the word per, and grabbing all after that, until the first dash "-" as the variable.   
   if per: # If the  search was successful...
      multiplier = 0
      if debugVerbosity >= 2: notify("Groups: {}. Count: {}".format(per.groups(),count)) #Debug
      if per.group(2) and (per.group(2) == 'Target' or per.group(2) == 'Every'): # If we're looking for a target or any specific type of card, we need to scour the requested group for targets.
         if debugVerbosity >= 2: notify("Checking for Targeted per")
         if per.group(2) == 'Target' and len(targetCards) == 0: 
            delayed_whisper(":::ERROR::: Script expected a card targeted but found none! Exiting with 0 multiplier.")
            # If we were expecting a target card and we have none we shouldn't even be in here. But in any case, we return a multiplier of 0
         elif per.group(2) == 'Every' and len(targetCards) == 0: pass #If we looking for a number of cards and we found none, then obviously we return 0
         else:
            if per.group(2) == 'Host': targetCards = [fetchHost(card)]
            for perCard in targetCards:
               if not checkSpecialRestrictions(Autoscript,perCard): continue
               if debugVerbosity >= 2: notify("perCard = {}".format(perCard))
               if re.search(r'Marker',per.group(3)):
                  markerName = re.search(r'Marker{([\w :]+)}',per.group(3)) # I don't understand why I had to make the curly brackets optional, but it seens atTurnStart/End completely eats them when it parses the CardsAS.get(card.model,'')
                  marker = findMarker(perCard, markerName.group(1))
                  if marker: multiplier += perCard.markers[marker]
               elif re.search(r'Property',per.group(3)):
                  property = re.search(r'Property{([\w ]+)}',per.group(3))
                  multiplier += num(perCard.properties[property.group(1)])
               else: multiplier += 1 # If there's no special conditions, then we just add one multiplier per valid (auto)target. Ef. "-perEvery-AutoTargeted-onICE" would give 1 multiplier per ICE on the table
         if per.group(2) == 'Every': # If we're checking every card of a specific trait, we may have cards that give bonus to that amount (e.g. Echo base), so we look for those bonuses now.
            for c in table: # We check for cards for give bonus objective traits (e.g. Echo Base)
               Autoscripts = CardsAS.get(c.model,'').split('||')
               for autoS in Autoscripts:
                  if debugVerbosity >= 2: notify("### Checking {} for Objective Trait boosting AS: {}".format(c,autoS))
                  TraitRegex = re.search(r'Trait\{([A-Za-z_ ]+)\}([0-9])Bonus',autoS)
                  if TraitRegex: 
                     if debugVerbosity >= 3: notify("TraitRegex found. Groups = {}".format(TraitRegex.groups()))
                     TraitsList = TraitRegex.group(1).split('_and_') # We make a list of all the traits the bonus effect of the cardprovides
                     if debugVerbosity >= 4: notify("### TraitsList = {}".format(TraitsList)) 
                     TraitsRestrictions = prepareRestrictions(Autoscript) # Then we gather the trait restrictions the original effect was looking for
                     if debugVerbosity >= 4: notify("### TraitsRestrictions = {}".format(TraitsRestrictions))
                     if checkCardRestrictions(TraitsList, TraitsRestrictions) and checkSpecialRestrictions(Autoscript,c): # Finally we compare the bonus traits of the card we found, wit  h the traits the original effect was polling for.
                        multiplier += num(TraitRegex.group(2)) * chkPlayer(autoS, c.controller, False, True) # If they match, we increase our multiplier by the relevant number, if the card has the appropriate controller according to its effect.
      else: #If we're not looking for a particular target, then we check for everything else.
         if debugVerbosity >= 2: notify("### Doing no table lookup") # Debug.
         if per.group(3) == 'X': multiplier = count # Probably not needed and the next elif can handle alone anyway.
         elif count: multiplier = num(count) * chkPlayer(Autoscript, card.controller, False) # All non-special-rules per<somcething> requests use this formula.
                                                                                              # Usually there is a count sent to this function (eg, number of favour purchased) with which to multiply the end result with
                                                                                              # and some cards may only work when a rival owns or does something.
         elif re.search(r'Marker',per.group(3)):
            markerName = re.search(r'Marker{([\w :]+)}',per.group(3)) # I don't understand why I had to make the curly brackets optional, but it seens atTurnStart/End completely eats them when it parses the CardsAS.get(card.model,'')
            marker = findMarker(card, markerName.group(1))
            if marker: multiplier = card.markers[marker]
            else: multiplier = 0
         elif re.search(r'Property',per.group(3)):
            property = re.search(r'Property{([\w ]+)}',per.group(3))
            multiplier = card.properties[property.group(1)]
      if debugVerbosity >= 2: notify("### Checking ignore") # Debug.            
      ignS = re.search(r'-ignore([0-9]+)',Autoscript)
      if ignS: ignore = num(ignS.group(1))
      if debugVerbosity >= 2: notify("### Checking div") # Debug.            
      divS = re.search(r'-div([0-9]+)',Autoscript)
      if divS: div = num(divS.group(1))
      if debugVerbosity >= 2: notify("### Checking max") # Debug.            
      maxS = re.search(r'-max([0-9]+)',Autoscript)
      if maxS: max = num(maxS.group(1))
   else: multiplier = 1
   finalMultiplier = (multiplier - ignore) / div
   if max and finalMultiplier > max: 
      debugNotify("Reducing Multiplier to Max",2)
      finalMultiplier = max
   if debugVerbosity >= 2: notify("<<< per() with Multiplier: {}".format(finalMultiplier)) # Debug
   return finalMultiplier
   
def chooseAnyToken(card,action):
   markerChoices = []
   if action == 'Remove' or action == 'Transfer':
      if card.markers[mdict['Shield']]: markerChoices.append("Shield")
      if card.markers[mdict['Focus']]: markerChoices.append("Focus")
      if card.markers[mdict['Damage']]: markerChoices.append("Damage")
   else: markerChoices = ["Shield","Focus","Damage"] # If we're adding any type of token, then we always provide a full choice list.
   if len(markerChoices) == 1: 
      token = mdict[markerChoices[0]]
   else:
      tokenChoice = SingleChoice("Choose one token to {} from {}.".format(action,card.name), markerChoices, type = 'button', default = 0)
      if tokenChoice == 'ABORT': return 'ABORT'
      token = mdict[markerChoices[tokenChoice]]
   return token
