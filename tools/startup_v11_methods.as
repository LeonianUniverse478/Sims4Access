      // BEGIN A11Y V11 STARTUP SOCKET (outbound only)
      // Speech transport for the main menu and Create a Sim before a save
      // loads, when PostServerCommand has no simulation to reach. Flash writes
      // narration lines to a loopback listener owned by our Python; Python
      // never writes back, so no socket data event is ever delivered into the
      // VM (the V10 request/response protocol coincided with five native
      // crashes at boot, at the menu and in CAS). Keyboard mode is signalled
      // by the port Python listens on: 45993 keyboard on, 45994 speech only.
      // Before a save loads, navigation keys are handled by the native
      // InputAction guards and queued for the next frame; no Python round trip.
      protected var mA11yStartupSocket:Object = null;
      protected var mA11yStartupConnected:Boolean = false;
      protected var mA11yStartupPort:int = 45993;
      protected var mA11yStartupNext:int = 0;
      protected var mA11yStartupOpenedAt:int = 0;
      protected var mA11yStartupInstalled:Boolean = false;
      protected var mA11yStartupPostWindow:int = 0;
      protected var mA11yStartupPostCount:int = 0;
      protected var mA11yStartupKeys:Array = new Array();
      protected var mA11yStartupActive:Boolean = false;
      protected var mA11yZoneSeen:Boolean = false;

      public function A11yStartupInstall() : void
      {
         try
         {
            if(this.mA11yStartupInstalled || this.mTooltipsLayer == null || this.mTooltipsLayer.stage == null) { return; }
            this.mA11yStartupInstalled = true;
            this.mTooltipsLayer.stage.addEventListener(Event.ENTER_FRAME,this.A11yStartupFrame,false,0,true);
         }
         catch(e:Error) { }
      }

      // True while no simulation client exists: from boot until the first
      // A11yHook (sent by Python at every zone load), and again whenever the
      // main menu dock is visible.
      public function A11yStartupZoneless() : Boolean
      {
         try
         {
            if(this.A11yIsLive(this.A11yLoadedWidget("GameEntryDock"))) { this.mA11yZoneSeen = false; return true; }
            return !this.mA11yZoneSeen;
         }
         catch(e:Error) { }
         return false;
      }

      public function A11yStartupClose(retryMs:int = 10000) : void
      {
         try
         {
            this.mA11yStartupConnected = false;
            this.mA11yStartupActive = false;
            this.mA11yStartupKeys.length = 0;
            if(this.mA11yStartupSocket != null)
            {
               this.mA11yStartupSocket["removeEventListener"]("connect",this.A11yStartupConnected);
               this.mA11yStartupSocket["removeEventListener"]("ioError",this.A11yStartupFailed);
               this.mA11yStartupSocket["removeEventListener"]("securityError",this.A11yStartupFailed);
               this.mA11yStartupSocket["removeEventListener"]("close",this.A11yStartupFailed);
               try { this.mA11yStartupSocket["close"](); } catch(closeError:Error) { }
            }
            this.mA11yStartupSocket = null;
            this.mA11yStartupNext = getTimer() + retryMs;
         }
         catch(e:Error) { }
      }

      public function A11yStartupWrite(line:String) : Boolean
      {
         try
         {
            if(this.mA11yStartupSocket == null || !this.mA11yStartupConnected || !this.mA11yStartupSocket["connected"] || line.length > 32768 || line.indexOf("\n") >= 0 || line.indexOf("\r") >= 0) { return false; }
            this.mA11yStartupSocket["writeUTFBytes"](line + "\n");
            this.mA11yStartupSocket["flush"]();
            return true;
         }
         catch(e:Error) { this.A11yStartupClose(5000); }
         return false;
      }

      public function A11yPostToPython(command:String, payload:String = "") : Object
      {
         try
         {
            var allowed:Array = ["a11y.speak_enc","a11y.widget_enc","a11y.focus_enc","a11y.widgetname_enc","a11y.dialog_enc","a11y.scope_enc","a11y.event_enc","a11y.context_enc","a11y.inspect_enc","a11y.modalstate","a11y.inputfence","a11y.stop","a11y.mark"];
            if(this.mA11yStartupActive && allowed.indexOf(command) >= 0)
            {
               var now:int = getTimer();
               if(now - this.mA11yStartupPostWindow >= 1000)
               {
                  this.mA11yStartupPostWindow = now;
                  this.mA11yStartupPostCount = 0;
               }
               // State messages cannot be lost behind noisy hovers.
               if(this.mA11yStartupPostCount >= 40 && command != "a11y.inputfence" && command != "a11y.modalstate") { return true; }
               this.mA11yStartupPostCount = this.mA11yStartupPostCount + 1;
               if(this.A11yStartupWrite("POST|" + command + "|" + payload)) { return true; }
            }
         }
         catch(e:Error) { }
         return CommunicationManager.PostServerCommand(command,payload);
      }

      public function A11yStartupConnected(event:Event) : void
      {
         try
         {
            if(event.currentTarget != this.mA11yStartupSocket) { return; }
            this.mA11yStartupConnected = true;
            this.mA11yStartupActive = this.A11yStartupZoneless();
            this.mA11yStartupKeys.length = 0;
            this.mA11yModalReported = "";
            this.mA11yOwnerReported = "";
            this.A11yStartupWrite("HELLO|A11Y_STARTUP_V2|" + this.mA11yStartupPort);
            if(this.mA11yStartupPort == 45993) { this.A11yKeyboardOn(); }
            else { this.A11yKeyboardOff(); }
            this.A11yPostToPython("a11y.mark","startup-v11-A11YLIBNAME-port" + this.mA11yStartupPort + (this.mA11yStartupActive ? "-active" : "-idle"));
         }
         catch(e:Error) { this.A11yStartupClose(5000); }
      }

      public function A11yStartupFailed(event:Event) : void
      {
         var wasConnected:Boolean = false;
         try
         {
            if(event.currentTarget != this.mA11yStartupSocket) { return; }
            wasConnected = this.mA11yStartupConnected;
            this.A11yStartupClose(wasConnected ? 5000 : 3000);
            // Refused before connecting: Python listens on the other port
            // (keyboard mode) or is not listening at all. Alternate.
            if(!wasConnected) { this.mA11yStartupPort = this.mA11yStartupPort == 45993 ? 45994 : 45993; }
         }
         catch(e:Error) { }
      }

      // Called from the native guard callback; the action runs on the next
      // frame, never inside EA's input dispatch.
      public function A11yStartupKey(key:int, modifier:int) : void
      {
         try
         {
            if(this.mA11yStartupKeys.length < 8) { this.mA11yStartupKeys.push(key * 10 + modifier); }
         }
         catch(e:Error) { }
      }

      public function A11yStartupDrainKeys() : void
      {
         var code:int = 0;
         var key:int = 0;
         var modifier:int = 0;
         try
         {
            while(this.mA11yStartupKeys.length > 0 && this.mA11yStartupActive && this.mA11yKeyboard)
            {
               code = int(this.mA11yStartupKeys.shift());
               key = int(code / 10);
               modifier = code - key * 10;
               if(key == 9) { this.A11yTabControl(modifier == 1 ? -1 : 1); }
               else if(key == 13) { this.A11yActivate(); }
               else if(key == 32) { this.A11yActivate(false); }
               else if(key == 8) { this.A11yReturnRow(); }
               else if(key == 27) { this.A11yEscape(); }
               else if(key == 38) { this.A11yArrowNav(-1); }
               else if(key == 40) { this.A11yArrowNav(1); }
               else if(key == 37) { this.A11yArrowHorizontal(-1); }
               else if(key == 39) { this.A11yArrowHorizontal(1); }
            }
            if(!this.mA11yStartupActive) { this.mA11yStartupKeys.length = 0; }
         }
         catch(e:Error) { this.mA11yStartupKeys.length = 0; }
      }

      public function A11yStartupFrame(event:Event = null) : void
      {
         var active:Boolean = false;
         try
         {
            var now:int = getTimer();
            if(this.mA11yStartupSocket != null)
            {
               if(!this.mA11yStartupConnected)
               {
                  if(now - this.mA11yStartupOpenedAt > 6000)
                  {
                     this.A11yStartupClose(3000);
                     this.mA11yStartupPort = this.mA11yStartupPort == 45993 ? 45994 : 45993;
                  }
                  return;
               }
               if(!this.mA11yStartupSocket["connected"]) { this.A11yStartupClose(5000); return; }
               active = this.A11yStartupZoneless();
               if(active != this.mA11yStartupActive)
               {
                  this.mA11yStartupActive = active;
                  this.mA11yStartupKeys.length = 0;
                  this.mA11yModalReported = "";
                  this.mA11yOwnerReported = "";
                  if(active) { this.A11yPostToPython("a11y.mark","startup-v11-active"); }
               }
               if(active && this.mA11yKeyboard)
               {
                  this.mA11yKeyboardLease = now + 2000;
                  this.A11yStartupDrainKeys();
               }
               return;
            }
            if(now < this.mA11yStartupNext) { return; }
            this.mA11yStartupNext = now + 10000;
            var socketClass:Class = getDefinitionByName("flash.net.Socket") as Class;
            this.mA11yStartupSocket = new socketClass();
            this.mA11yStartupOpenedAt = now;
            this.mA11yStartupSocket["addEventListener"]("connect",this.A11yStartupConnected);
            this.mA11yStartupSocket["addEventListener"]("ioError",this.A11yStartupFailed);
            this.mA11yStartupSocket["addEventListener"]("securityError",this.A11yStartupFailed);
            this.mA11yStartupSocket["addEventListener"]("close",this.A11yStartupFailed);
            try { this.mA11yStartupSocket["timeout"] = 6000; } catch(timeoutError:Error) { }
            this.mA11yStartupSocket["connect"]("127.0.0.1",this.mA11yStartupPort);
         }
         catch(e:Error) { this.A11yStartupClose(10000); }
      }
      // END A11Y V11 STARTUP SOCKET
