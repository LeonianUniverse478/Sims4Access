      // Native key actions consume game input; Python supplies deliberate
      // press/repeat/release messages. No controller-mode changes or EXE hooks.
      protected var mA11yKeyboard:Boolean = false;
      protected var mA11yNativeActions:Array = new Array();
      protected var mA11yGuardHeld:Object = new Object();
      protected var mA11yHudRoot:DisplayObject = null;
      protected var mA11yHudButton:DisplayObject = null;
      protected var mA11yListMemory:Dictionary = new Dictionary(true);
      protected var mA11yFocusDue:int = 0;
      protected var mA11yFocusPending:DisplayObject = null;

      public function A11yKeyboardOn(param1:Object = null) : void
      {
         try { this.mA11yKeyboard = true; this.mA11yAutoFocus = true; this.A11yInstallKeyGuards(); this.A11yModalFrame(); }
         catch(e:Error) { }
      }

      public function A11yKeyboardOff(param1:Object = null) : void
      {
         try
         {
            this.mA11yKeyboard = false;
            this.mA11yAutoFocus = false;
            this.mA11yGuardHeld = new Object();
            this.A11yClearFocus();
            this.mA11yScope = null;
            this.mA11yPendingScope = null;
            this.mA11yActiveModalRoot = null;
            this.mA11yScopeHistory.length = 0;
            this.mA11yFocusPending = null;
            this.A11yModalFrame();
         }
         catch(e:Error) { }
      }

      public function A11yEditing() : Boolean
      {
         try { return this.mTooltipsLayer.stage.focus is TextField && TextField(this.mTooltipsLayer.stage.focus).type == "input"; }
         catch(e:Error) { }
         return false;
      }

      public function A11yGuardValid(key:int) : Boolean
      {
         try
         {
            if(!this.mA11yKeyboard) { return false; }
            if(this.mA11yGuardHeld[key]) { return true; }
            if(this.A11yEditing() && key != 9 && key != 27) { return false; }
            if(this.A11yIsModalScope(this.mA11yPendingScope) || this.A11yIsModalScope(this.mA11yScope)) { return true; }
            // Tab enters HUD controls from gameplay, never steals text editing.
            return key == 9 && !this.A11yEditing() && this.A11yLoadedWidget("SimInfoTray") != null;
         }
         catch(e:Error) { }
         return false;
      }

      public function A11yGuardCheck(key:int) : Function
      {
         var self:TooltipManager = this;
         return function():Boolean { return self.A11yGuardValid(key); };
      }

      public function A11yGuardConsume(key:int) : Function
      {
         var self:TooltipManager = this;
         return function():Boolean
         {
            try { self.mA11yGuardHeld[key] = true; } catch(e:Error) { }
            // InputAction.TriggerActions inverts callback results: false consumes.
            return false;
         };
      }

      public function A11yInstallKeyGuards() : void
      {
         var actionClass:Object = null;
         var triggerClass:Object = null;
         var manager:Object = null;
         var action:Object = null;
         var keys:Array = [9,13,27,32,37,38,39,40];
         var i:int = 0;
         var modifier:int = 0;
         try
         {
            if(this.mA11yNativeActions.length > 0) { return; }
            actionClass = getDefinitionByName("olympus.input.InputAction");
            triggerClass = getDefinitionByName("olympus.input.InputTrigger");
            manager = getDefinitionByName("olympus.io.InputActionManager");
            while(i < keys.length)
            {
               modifier = 0;
               while(modifier < (keys[i] == 9 ? 2 : 1))
               {
                  action = actionClass["WhenTriggered"](triggerClass["FromKeyBinding"](keys[i],modifier));
                  action["SetPriority"](1000000);
                  action["AllowWhileModalOpen"](true);
                  action["SetValidCheck"](this.A11yGuardCheck(keys[i]));
                  action["CallFunction"](this.A11yGuardConsume(keys[i]));
                  if(manager["RegisterAction"](action)) { this.mA11yNativeActions.push(action); }
                  modifier = modifier + 1;
               }
               i = i + 1;
            }
            CommunicationManager.PostServerCommand("a11y.mark","keyboard-native-guards-" + this.mA11yNativeActions.length);
         }
         catch(e:Error) { CommunicationManager.PostServerCommand("a11y.mark","keyboard-guard-error"); }
      }

      public function A11yLoadedWidget(name:String) : DisplayObject
      {
         try { if(this.mA11yLayoutManager != null) { return this.mA11yLayoutManager["GetLoadedWidgetByName"](name) as DisplayObject; } }
         catch(e:Error) { }
         return null;
      }

      public function A11yPersistentHud(name:String) : Boolean
      {
         return ["SimInfoTray","SimHub","TimeControls","InteractionQueue","ObjectBoundElements","Notifications","HUDLibrary","UIContainer"].indexOf(name) >= 0;
      }

      public function A11yOpenHud() : DisplayObject
      {
         var tray:Object = this.A11yLoadedWidget("SimInfoTray");
         var names:Array = ["btnSIMotivePanel","btnSISkillPanel","btnSIRelationshipPanel","btnSICareerPanel","btnSIInventoryPanel","btnSIAspirationPanel","btnSISummaryPanel","btnSIClubPanel","btnHIVenuePanel"];
         var button:Object = null;
         var panel:DisplayObject = null;
         var i:int = 0;
         try
         {
            if(!this.A11yIsLive(tray as DisplayObject)) { return null; }
            panel = tray["mcPhoneAlert"] as DisplayObject;
            if(this.A11yIsLive(panel)) { this.mA11yHudButton = tray["btnPhone"]; return panel; }
            panel = tray["mcPhonePanel"] as DisplayObject;
            if(this.A11yIsLive(panel)) { this.mA11yHudButton = tray["btnPhone"]; return panel; }
            while(i < names.length)
            {
               button = tray[names[i]];
               if(button != null && button["Selected"])
               {
                  panel = this.A11yLoadedWidget(button["PanelName"]);
                  if(this.A11yIsLive(panel)) { this.mA11yHudButton = button as DisplayObject; return panel; }
               }
               i = i + 1;
            }
         }
         catch(e:Error) { }
         return null;
      }

      public function A11yInformational(item:DisplayObject) : Boolean
      {
         var name:String = null;
         try
         {
            name = getQualifiedClassName(item);
            if(name.indexOf("ProfileDataCell") >= 0) { return true; }
            if(name.indexOf("Calendar.controls::Schedule") >= 0 && name.indexOf("Entry") >= 0) { return true; }
            if(name.indexOf("CommodityContainer") >= 0 || name.indexOf("Moodlet") >= 0 && name.indexOf("Container") < 0) { return true; }
            if(item is TextField) { return false; }
            if("TooltipExt" in item && Object(item)["TooltipExt"]["Text"] != null && String(Object(item)["TooltipExt"]["Text"]).length > 0) { return true; }
         }
         catch(e:Error) { }
         return false;
      }

      public function A11yTabControl(direction:int) : void
      {
         var all:Array = new Array();
         var groups:Array = new Array();
         var owners:Array = new Array();
         var list:Object = null;
         var owner:Object = null;
         var current:Object = null;
         var target:DisplayObject = null;
         var index:int = -1;
         var i:int = 0;
         try
         {
            if(!this.mA11yKeyboard) { return; }
            this.A11yModalFrame();
            if(this.mA11yPendingScope != null || this.mA11yIdxDir != 0) { this.mA11yNavQueue.push(direction * 3); return; }
            list = this.A11yFindScrollList(this.mA11yFocused);
            if(list != null) { this.mA11yListMemory[list] = this.mA11yLogicalIndex; }
            current = list != null ? list : this.mA11yFocused;
            this.A11yCollectFocusables(this.mA11yScope != null ? this.mA11yScope : this.mTooltipsLayer.stage,all,0);
            all.sort(this.A11ySortFocusables);
            while(i < all.length)
            {
               list = this.A11yFindScrollList(all[i]);
               owner = list != null ? list : all[i];
               if(owners.indexOf(owner) < 0) { owners.push(owner); groups.push(all[i]); }
               i = i + 1;
            }
            if(groups.length == 0) { return; }
            index = owners.indexOf(current);
            index = index < 0 ? (direction > 0 ? 0 : groups.length - 1) : (index + direction + groups.length) % groups.length;
            target = groups[index];
            list = this.A11yFindScrollList(target);
            if(list != null)
            {
               i = this.mA11yListMemory[list] != undefined ? int(this.mA11yListMemory[list]) : 0;
               i = Math.max(0,Math.min(i,int(list["mGridLayout"]["GetNumItems"]()) - 1));
               if(this.A11yRequestIndex(list,i,direction)) { return; }
            }
            this.A11yFocusItem(target);
         }
         catch(e:Error) { }
      }

      public function A11yMsgTabNext(param1:Object = null) : void
      {
         try { this.A11yTabControl(1); } catch(e:Error) { }
      }

      public function A11yMsgTabPrev(param1:Object = null) : void
      {
         try { this.A11yTabControl(-1); } catch(e:Error) { }
      }

      public function A11yRevealControl(item:DisplayObject) : void
      {
         var node:Object = item != null ? item.parent : null;
         var view:DisplayObjectContainer = null;
         var slider:Object = null;
         var bounds:Rectangle = null;
         var viewport:Rectangle = null;
         var offset:Number = 0;
         try
         {
            while(node != null)
            {
               view = null;
               slider = null;
               if("mcView" in node && "mcSlider" in node) { view = node["mcView"] as DisplayObjectContainer; slider = node["mcSlider"]; }
               if("mcScheduleView" in node && "mcScheduleSlider" in node) { view = node["mcScheduleView"] as DisplayObjectContainer; slider = node["mcScheduleSlider"]; }
               if(view != null && slider != null && "mcMask" in view)
               {
                  bounds = item.getBounds(view);
                  viewport = Object(view)["mcMask"].getBounds(view);
                  offset = bounds.top < viewport.top ? bounds.top - viewport.top : (bounds.bottom > viewport.bottom ? bounds.bottom - viewport.bottom : 0);
                  if(offset != 0) { slider["SetCurrentValue"](Number(slider["Value"]) + offset,true,false,true); }
               }
               node = node.parent;
            }
         }
         catch(e:Error) { }
      }

      public function A11yFocusSettled() : void
      {
         try
         {
            if(this.mA11yFocusPending == null || getTimer() < this.mA11yFocusDue || this.mA11yIdxDir != 0 || this.mA11yNavQueue.length > 0) { return; }
            if(this.mA11yFocusPending == this.mA11yFocused && this.A11yIsLive(this.mA11yFocused))
            {
               this.A11yDrawFocusRing(this.mA11yFocused);
               this.mA11yLast = "";
               this.A11yAnnounceDisplay(this.mA11yFocused,"a11y.focus_enc",true);
            }
            this.mA11yFocusPending = null;
         }
         catch(e:Error) { this.mA11yFocusPending = null; }
      }
