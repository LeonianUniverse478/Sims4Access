      // BEGIN A11Y V10 STARTUP SOCKET
      protected var mA11yStartupSocket:Object = null;
      protected var mA11yStartupReady:Boolean = false;
      protected var mA11yStartupActive:Boolean = false;
      protected var mA11yStartupInput:String = "";
      protected var mA11yStartupNext:int = 0;
      protected var mA11yStartupHeard:int = 0;
      protected var mA11yStartupPing:int = 0;
      protected var mA11yStartupInstalled:Boolean = false;
      protected var mA11yStartupPostWindow:int = 0;
      protected var mA11yStartupPostCount:int = 0;
      protected var mA11yStartupFence:Boolean = false;

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

      public function A11yStartupClose() : void
      {
         try
         {
            if(this.mA11yStartupActive)
            {
               this.mA11yKeyboardLease = 0;
               this.mA11yGuardHeld = new Object();
            }
            this.mA11yStartupActive = false;
            this.mA11yStartupReady = false;
            this.mA11yStartupFence = false;
            this.mA11yStartupInput = "";
            if(this.mA11yStartupSocket != null)
            {
               this.mA11yStartupSocket["removeEventListener"]("connect",this.A11yStartupConnected);
               this.mA11yStartupSocket["removeEventListener"]("socketData",this.A11yStartupData);
               this.mA11yStartupSocket["removeEventListener"]("ioError",this.A11yStartupFailed);
               this.mA11yStartupSocket["removeEventListener"]("securityError",this.A11yStartupFailed);
               this.mA11yStartupSocket["removeEventListener"]("close",this.A11yStartupFailed);
               try { this.mA11yStartupSocket["close"](); } catch(closeError:Error) { }
            }
            this.mA11yStartupSocket = null;
            this.mA11yStartupNext = getTimer() + 5000;
         }
         catch(e:Error) { }
      }

      public function A11yStartupWrite(line:String) : Boolean
      {
         try
         {
            if(this.mA11yStartupSocket == null || !this.mA11yStartupSocket["connected"] || line.length > 32768 || line.indexOf("\n") >= 0 || line.indexOf("\r") >= 0) { return false; }
            this.mA11yStartupSocket["writeUTFBytes"](line + "\n");
            this.mA11yStartupSocket["flush"]();
            return true;
         }
         catch(e:Error) { this.A11yStartupClose(); }
         return false;
      }

      public function A11yPostToPython(command:String, payload:String = "") : Object
      {
         try
         {
            var allowed:Array = ["a11y.speak_enc","a11y.widget_enc","a11y.focus_enc","a11y.widgetname_enc","a11y.dialog_enc","a11y.scope_enc","a11y.event_enc","a11y.context_enc","a11y.inspect_enc","a11y.modalstate","a11y.inputfence","a11y.stop","a11y.mark"];
            if(this.mA11yStartupActive && this.mA11yStartupReady && allowed.indexOf(command) >= 0)
            {
               if(command == "a11y.inputfence") { this.mA11yStartupFence = true; }
               var now:int = getTimer();
               if(now - this.mA11yStartupPostWindow >= 1000)
               {
                  this.mA11yStartupPostWindow = now;
                  this.mA11yStartupPostCount = 0;
               }
               // State/fence messages cannot be lost behind noisy hovers.
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
            this.mA11yStartupHeard = getTimer();
            this.A11yStartupWrite("HELLO|A11Y_STARTUP_V1");
         }
         catch(e:Error) { this.A11yStartupClose(); }
      }

      public function A11yStartupFailed(event:Event) : void
      {
         try { if(event.currentTarget == this.mA11yStartupSocket) { this.A11yStartupClose(); } }
         catch(e:Error) { }
      }

      public function A11yStartupNavigation(message:String) : Boolean
      {
         try
         {
            var allowed:Array = ["A11yTabNext","A11yTabPrev","A11yNavNext","A11yNavPrev","A11yArrowUp","A11yArrowDown","A11yArrowLeft","A11yArrowRight","A11yActivate","A11yToggle","A11yReturnRow","A11yEscape","A11yDismiss","A11yReadCurrent","A11yReadDialog","A11yClearFocus","A11yInspect","A11yKeyboardOn","A11yKeyboardOff","A11yAutoFocusOn","A11yAutoFocusOff","A11yHook","A11yKeyProbeOn","A11yKeyProbeOff","A11y|lease"];
            if(allowed.indexOf(message) >= 0)
            {
               if(this.mA11yStartupFence && (message == "A11yActivate" || message == "A11yToggle")) { return true; }
               this.A11yOnGameMessage(message);
               return true;
            }
            if(message.indexOf("A11y|keyup|") == 0)
            {
               var key:String = message.substr(11);
               if(["9","13","27","32","37","38","39","40","8"].indexOf(key) >= 0)
               {
                  this.A11yHandleEncoded(message);
                  return true;
               }
            }
         }
         catch(e:Error) { }
         return false;
      }

      public function A11yStartupData(event:Event) : void
      {
         try
         {
            if(event.currentTarget != this.mA11yStartupSocket) { return; }
            var available:int = int(this.mA11yStartupSocket["bytesAvailable"]);
            if(available < 0 || available > 65536 || this.mA11yStartupInput.length + available > 65536) { this.A11yStartupClose(); return; }
            this.mA11yStartupInput = this.mA11yStartupInput + this.mA11yStartupSocket["readUTFBytes"](available);
            this.mA11yStartupHeard = getTimer();
            var end:int = this.mA11yStartupInput.indexOf("\n");
            while(end >= 0)
            {
               var line:String = this.mA11yStartupInput.substr(0,end);
               this.mA11yStartupInput = this.mA11yStartupInput.substr(end + 1);
               if(line.indexOf("CHALLENGE|") == 0 && line.length == 42 && !this.mA11yStartupReady)
               {
                  this.A11yStartupWrite("CONFIRM|" + line.substr(10));
               }
               else if(line == "READY")
               {
                  this.mA11yStartupReady = true;
                  this.mA11yStartupPing = 0;
               }
               else if(line == "PONG") { }
               else if(line == "FENCE|ACK" && this.mA11yStartupReady) { this.mA11yStartupFence = false; }
               else if(line.indexOf("CONFIG|") == 0 && this.mA11yStartupReady)
               {
                  var fields:Array = line.split("|");
                  if(fields.length != 4 || ["0","1"].indexOf(fields[1]) < 0 || ["0","1"].indexOf(fields[2]) < 0 || ["0","1"].indexOf(fields[3]) < 0) { this.A11yStartupClose(); return; }
                  var wasActive:Boolean = this.mA11yStartupActive;
                  this.mA11yStartupActive = fields[1] == "1";
                  if(wasActive != this.mA11yStartupActive) { this.mA11yStartupFence = false; }
                  if(this.mA11yStartupActive)
                  {
                     if(fields[2] == "1") { this.A11yKeyboardOn(); } else { this.A11yKeyboardOff(); }
                     this.mA11yModalReported = "";
                     this.mA11yOwnerReported = "";
                     if(!wasActive) { this.A11yPostToPython("a11y.mark","startup-socket-A11YLIBNAME"); }
                  }
               }
               else if(line.indexOf("NAV|") == 0 && this.mA11yStartupReady)
               {
                  if(this.mA11yStartupActive && !this.A11yStartupNavigation(line.substr(4))) { this.A11yStartupClose(); return; }
               }
               else { this.A11yStartupClose(); return; }
               end = this.mA11yStartupInput.indexOf("\n");
            }
         }
         catch(e:Error) { this.A11yStartupClose(); }
      }

      public function A11yStartupFrame(event:Event = null) : void
      {
         try
         {
            var now:int = getTimer();
            if(this.mA11yStartupSocket != null)
            {
               if(now - this.mA11yStartupHeard > 8000) { this.A11yStartupClose(); return; }
               if(this.mA11yStartupReady && now >= this.mA11yStartupPing)
               {
                  this.mA11yStartupPing = now + 1000;
                  this.A11yStartupWrite("PING");
               }
               return;
            }
            if(now < this.mA11yStartupNext) { return; }
            this.mA11yStartupNext = now + 5000;
            var socketClass:Class = getDefinitionByName("flash.net.Socket") as Class;
            this.mA11yStartupSocket = new socketClass();
            this.mA11yStartupHeard = now;
            this.mA11yStartupSocket["addEventListener"]("connect",this.A11yStartupConnected);
            this.mA11yStartupSocket["addEventListener"]("socketData",this.A11yStartupData);
            this.mA11yStartupSocket["addEventListener"]("ioError",this.A11yStartupFailed);
            this.mA11yStartupSocket["addEventListener"]("securityError",this.A11yStartupFailed);
            this.mA11yStartupSocket["addEventListener"]("close",this.A11yStartupFailed);
            try { this.mA11yStartupSocket["timeout"] = 6000; } catch(timeoutError:Error) { }
            this.mA11yStartupSocket["connect"]("127.0.0.1",45993);
         }
         catch(e:Error) { this.A11yStartupClose(); }
      }
      // END A11Y V10 STARTUP SOCKET
