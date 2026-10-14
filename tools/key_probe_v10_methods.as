      // Optional diagnostics only. Never dispatches navigation, cancels an
      // event, or reads charCode/text. Off until A11yKeyProbeOn is requested.
      protected var mA11yKeyProbeEnabled:Boolean = false;
      protected var mA11yKeyProbeStage:Stage = null;
      protected var mA11yKeyProbeActions:Array = new Array();
      protected var mA11yKeyProbeHeld:Object = new Object();
      protected var mA11yKeyProbeLastEvent:Event = null;
      protected var mA11yKeyProbeUntil:int = 0;
      protected var mA11yKeyProbeCount:int = 0;

      public function A11yKeyProbeReport(source:String, key:int, location:int, control:Boolean, alt:Boolean, shift:Boolean, down:Boolean) : void
      {
         try
         {
            if(!this.mA11yKeyProbeEnabled || this.mA11yKeyProbeCount >= 200) { return; }
            this.mA11yKeyProbeCount = this.mA11yKeyProbeCount + 1;
            this.A11yPostToPython("a11y.mark","keyprobe-" + source + "-" + (down ? "down" : "up") + "|" + key + "|" + location + "|" + (control ? "1" : "0") + "|" + (alt ? "1" : "0") + "|" + (shift ? "1" : "0"));
         }
         catch(e:Error) { }
      }

      public function A11yKeyProbeStageEvent(event:KeyboardEvent) : void
      {
         var key:int = int(event.keyCode);
         var down:Boolean = event.type == KeyboardEvent.KEY_DOWN;
         var chordKeys:Array = [8,13,33,34,37,38,39,40,66,69,70,71,72,80,82,83,84,87,89,90,219,221];
         try
         {
            // Capture observes focused descendants; bubble observes a key
            // whose target is the Stage itself. Process that event once.
            if(!this.mA11yKeyProbeEnabled || event == this.mA11yKeyProbeLastEvent) { return; }
            this.mA11yKeyProbeLastEvent = event;
            if([16,17,18].indexOf(key) < 0 && !this.mA11yKeyProbeHeld[key] && !(event.ctrlKey && event.altKey && chordKeys.indexOf(key) >= 0)) { return; }
            if(down) { this.mA11yKeyProbeHeld[key] = true; }
            else { delete this.mA11yKeyProbeHeld[key]; }
            this.A11yKeyProbeReport("stage",key,int(event.keyLocation),event.ctrlKey,event.altKey,event.shiftKey,down);
         }
         catch(e:Error) { }
      }

      public function A11yKeyProbeNative() : Boolean
      {
         try
         {
            // This trigger supplies no left/right Alt information. -1 is
            // deliberately unknown, not a claimed KeyboardEvent location.
            this.A11yKeyProbeReport("native",72,-1,true,true,false,true);
         }
         catch(e:Error) { }
         // EA's TriggerActions negates this result: true does NOT consume.
         return true;
      }

      public function A11yKeyProbeValid() : Boolean
      {
         try { return this.mA11yKeyProbeEnabled && getTimer() <= this.mA11yKeyProbeUntil; }
         catch(e:Error) { }
         return false;
      }

      public function A11yKeyProbeTick(event:Event) : void
      {
         try { if(event.type == Event.DEACTIVATE || getTimer() > this.mA11yKeyProbeUntil) { this.A11yKeyProbeOff(); } }
         catch(e:Error) { }
      }

      public function A11yKeyProbeOn(param1:Object = null) : void
      {
         var actionClass:Object = null;
         var triggerClass:Object = null;
         var manager:Object = null;
         var action:Object = null;
         try
         {
            this.A11yKeyProbeOff();
            if(this.mTooltipsLayer == null || this.mTooltipsLayer.stage == null) { return; }
            this.mA11yKeyProbeStage = this.mTooltipsLayer.stage;
            this.mA11yKeyProbeEnabled = true;
            this.mA11yKeyProbeUntil = getTimer() + 60000;
            this.mA11yKeyProbeCount = 0;
            this.mA11yKeyProbeStage.addEventListener(KeyboardEvent.KEY_DOWN,this.A11yKeyProbeStageEvent,true,1000001,true);
            this.mA11yKeyProbeStage.addEventListener(KeyboardEvent.KEY_DOWN,this.A11yKeyProbeStageEvent,false,1000001,true);
            this.mA11yKeyProbeStage.addEventListener(KeyboardEvent.KEY_UP,this.A11yKeyProbeStageEvent,true,1000001,true);
            this.mA11yKeyProbeStage.addEventListener(KeyboardEvent.KEY_UP,this.A11yKeyProbeStageEvent,false,1000001,true);
            this.mA11yKeyProbeStage.addEventListener(Event.ENTER_FRAME,this.A11yKeyProbeTick,false,0,true);
            this.mA11yKeyProbeStage.addEventListener(Event.DEACTIVATE,this.A11yKeyProbeTick,false,0,true);
            actionClass = getDefinitionByName("olympus.input.InputAction");
            triggerClass = getDefinitionByName("olympus.input.InputTrigger");
            manager = getDefinitionByName("olympus.io.InputActionManager");
            action = actionClass["WhenTriggered"](triggerClass["FromKeyBinding"](72,6));
            action["SetPriority"](1000001);
            action["AllowWhileModalOpen"](true);
            action["SetValidCheck"](this.A11yKeyProbeValid);
            action["CallFunction"](this.A11yKeyProbeNative);
            if(manager["RegisterAction"](action)) { this.mA11yKeyProbeActions.push(action); }
            this.A11yPostToPython("a11y.mark","keyprobe-on-60s-native-actions-" + this.mA11yKeyProbeActions.length);
         }
         catch(e:Error) { this.A11yKeyProbeOff(); }
      }

      public function A11yKeyProbeOff(param1:Object = null) : void
      {
         var manager:Object = null;
         var action:Object = null;
         var wasEnabled:Boolean = this.mA11yKeyProbeEnabled;
         try
         {
            this.mA11yKeyProbeEnabled = false;
            if(this.mA11yKeyProbeStage != null)
            {
               this.mA11yKeyProbeStage.removeEventListener(KeyboardEvent.KEY_DOWN,this.A11yKeyProbeStageEvent,true);
               this.mA11yKeyProbeStage.removeEventListener(KeyboardEvent.KEY_DOWN,this.A11yKeyProbeStageEvent,false);
               this.mA11yKeyProbeStage.removeEventListener(KeyboardEvent.KEY_UP,this.A11yKeyProbeStageEvent,true);
               this.mA11yKeyProbeStage.removeEventListener(KeyboardEvent.KEY_UP,this.A11yKeyProbeStageEvent,false);
               this.mA11yKeyProbeStage.removeEventListener(Event.ENTER_FRAME,this.A11yKeyProbeTick,false);
               this.mA11yKeyProbeStage.removeEventListener(Event.DEACTIVATE,this.A11yKeyProbeTick,false);
            }
            manager = getDefinitionByName("olympus.io.InputActionManager");
            while(this.mA11yKeyProbeActions.length > 0)
            {
               action = this.mA11yKeyProbeActions.pop();
               try { manager["UnregisterAction"](action); }
               catch(removeError:Error) { }
            }
            this.mA11yKeyProbeStage = null;
            this.mA11yKeyProbeHeld = new Object();
            this.mA11yKeyProbeLastEvent = null;
            if(wasEnabled) { this.A11yPostToPython("a11y.mark","keyprobe-off"); }
         }
         catch(e:Error) { }
      }
