      // Isolated capability test; never included in the normal build.
      protected var mA11ySocketProbeLabel:TextField = null;
      protected var mA11ySocketProbe:Object = null;
      protected var mA11ySocketProbeNext:int = 0;
      protected var mA11ySocketProbeCount:int = 0;
      protected var mA11ySocketProbeStatus:String = "not attempted";
      protected var mA11ySocketProbeInput:String = "";
      protected var mA11ySocketProbeDone:Boolean = false;

      public function A11ySocketProbeInstall() : void
      {
         try
         {
            if(this.mA11ySocketProbeLabel != null) { return; }
            this.mA11ySocketProbeLabel = new TextField();
            this.mA11ySocketProbeLabel.name = "a11ySocketProbe";
            this.mA11ySocketProbeLabel.mouseEnabled = false;
            this.mA11ySocketProbeLabel.selectable = false;
            this.mA11ySocketProbeLabel.embedFonts = true;
            this.mA11ySocketProbeLabel.defaultTextFormat = new TextFormat("$TextFont",18,0xFFFFFF);
            this.mA11ySocketProbeLabel.background = true;
            this.mA11ySocketProbeLabel.backgroundColor = 0x102040;
            this.mA11ySocketProbeLabel.width = 1300;
            this.mA11ySocketProbeLabel.height = 95;
            this.mA11ySocketProbeLabel.x = 24;
            this.mA11ySocketProbeLabel.y = 24;
            this.mTooltipsLayer.stage.addChild(this.mA11ySocketProbeLabel);
            this.mTooltipsLayer.stage.addEventListener(Event.ENTER_FRAME,this.A11ySocketProbeFrame,false,0,true);
         }
         catch(e:Error) { }
      }

      public function A11ySocketProbeConnected(event:Event) : void
      {
         try
         {
            if(event.currentTarget != this.mA11ySocketProbe) { return; }
            this.mA11ySocketProbeStatus = "connected; HELLO sent, awaiting challenge";
            this.mA11ySocketProbe["writeUTFBytes"]("A11Y_SOCKET_V10\n");
            this.mA11ySocketProbe["flush"]();
         }
         catch(e:Error) { this.mA11ySocketProbeStatus = "send error: " + e.message; }
      }

      public function A11ySocketProbeData(event:Event) : void
      {
         try
         {
            if(event.currentTarget != this.mA11ySocketProbe) { return; }
            var available:int = int(this.mA11ySocketProbe["bytesAvailable"]);
            if(available < 0 || available > 256 || this.mA11ySocketProbeInput.length + available > 256)
            {
               this.mA11ySocketProbeStatus = "invalid response length";
               this.mA11ySocketProbe["close"]();
               return;
            }
            this.mA11ySocketProbeInput = this.mA11ySocketProbeInput + this.mA11ySocketProbe["readUTFBytes"](available);
            var end:int = this.mA11ySocketProbeInput.indexOf("\n");
            while(end >= 0)
            {
               var line:String = this.mA11ySocketProbeInput.substr(0,end);
               this.mA11ySocketProbeInput = this.mA11ySocketProbeInput.substr(end + 1);
               if(line.indexOf("CHALLENGE|") == 0 && line.length == 42)
               {
                  this.mA11ySocketProbeStatus = "challenge received; confirmation sent";
                  this.mA11ySocketProbe["writeUTFBytes"]("CONFIRM|" + line.substr(10) + "\n");
                  this.mA11ySocketProbe["flush"]();
               }
               else if(line == "COMPLETE")
               {
                  this.mA11ySocketProbeDone = true;
                  this.mA11ySocketProbeStatus = "ROUNDTRIP VERIFIED - fixed Socket handshake complete";
                  this.mA11ySocketProbeLabel.backgroundColor = 0x105020;
               }
               else
               {
                  this.mA11ySocketProbeStatus = "unexpected diagnostic response";
                  this.mA11ySocketProbe["close"]();
                  return;
               }
               end = this.mA11ySocketProbeInput.indexOf("\n");
            }
         }
         catch(e:Error) { this.mA11ySocketProbeStatus = "receive error: " + e.message; }
      }

      public function A11ySocketProbeFailed(event:Event) : void
      {
         try
         {
            if(event.currentTarget != this.mA11ySocketProbe || this.mA11ySocketProbeDone) { return; }
            this.mA11ySocketProbeStatus = String(event).substr(0,170);
         }
         catch(e:Error) { }
      }

      public function A11ySocketProbeFrame(event:Event = null) : void
      {
         try
         {
            this.mA11ySocketProbeLabel.text = "STARTUP SOCKET V10 / Gamedata / attempt " + this.mA11ySocketProbeCount +
               "\n" + this.mA11ySocketProbeStatus;
            if(this.mA11ySocketProbeDone || this.mA11ySocketProbeCount >= 12 || getTimer() < this.mA11ySocketProbeNext) { return; }
            this.mA11ySocketProbeNext = getTimer() + 10000;
            this.mA11ySocketProbeCount = this.mA11ySocketProbeCount + 1;
            if(this.mA11ySocketProbe != null)
            {
               try { this.mA11ySocketProbe["close"](); } catch(closeError:Error) { }
            }
            this.mA11ySocketProbeInput = "";
            try
            {
               var socketClass:Class = getDefinitionByName("flash.net.Socket") as Class;
               this.mA11ySocketProbeStatus = "Socket class found; constructing";
               this.mA11ySocketProbe = new socketClass();
               this.mA11ySocketProbe["addEventListener"]("connect",this.A11ySocketProbeConnected);
               this.mA11ySocketProbe["addEventListener"]("socketData",this.A11ySocketProbeData);
               this.mA11ySocketProbe["addEventListener"]("ioError",this.A11ySocketProbeFailed);
               this.mA11ySocketProbe["addEventListener"]("securityError",this.A11ySocketProbeFailed);
               this.mA11ySocketProbe["addEventListener"]("close",this.A11ySocketProbeFailed);
               try { this.mA11ySocketProbe["timeout"] = 8000; } catch(timeoutError:Error) { }
               try
               {
                  var security:Object = getDefinitionByName("flash.system.Security");
                  security["loadPolicyFile"]("xmlsocket://127.0.0.1:45992");
               }
               catch(policyError:Error) { }
               this.mA11ySocketProbeStatus = "constructed; connect to loopback pending";
               this.mA11ySocketProbe["connect"]("127.0.0.1",45992);
            }
            catch(connectError:Error)
            {
               this.mA11ySocketProbeStatus = "capability error: " + connectError.message;
            }
         }
         catch(e:Error) { }
      }
