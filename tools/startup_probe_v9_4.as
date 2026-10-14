      // Temporary startup transport diagnostic. Not in the normal build.
      protected var mA11yProbeLabel:TextField = null;
      protected var mA11yProbeNext:int = 0;
      protected var mA11yProbeFrames:int = 0;
      protected var mA11yProbeDebug:int = 0;
      protected var mA11yProbeLoader:Object = null;
      protected var mA11yProbeStatus:String = "not attempted";

      public function A11yStartupProbeInstall() : void
      {
         try
         {
            if(this.mA11yProbeLabel != null) { return; }
            this.mA11yProbeLabel = new TextField();
            this.mA11yProbeLabel.name = "a11yStartupProbe";
            this.mA11yProbeLabel.mouseEnabled = false;
            this.mA11yProbeLabel.selectable = false;
            this.mA11yProbeLabel.embedFonts = true;
            this.mA11yProbeLabel.defaultTextFormat = new TextFormat("$TextFont",18,0xFFFFFF);
            this.mA11yProbeLabel.background = true;
            this.mA11yProbeLabel.backgroundColor = 0x102040;
            this.mA11yProbeLabel.width = 1100;
            this.mA11yProbeLabel.height = 85;
            this.mA11yProbeLabel.x = 24;
            this.mA11yProbeLabel.y = 24;
            this.mTooltipsLayer.stage.addChild(this.mA11yProbeLabel);
            this.mTooltipsLayer.stage.addEventListener(Event.ENTER_FRAME,this.A11yStartupProbeFrame,false,0,true);
            var debug:Object = getDefinitionByName("olympus.io.DebugCommands");
            debug["Register"]("ui.a11y.startup_probe",this.A11yStartupProbeDebug,"A11Y_STARTUP_V94_SENTINEL","Updates a diagnostic counter only.");
         }
         catch(e:Error) { this.mA11yProbeStatus = "setup error: " + e.message; }
      }

      public function A11yStartupProbeDebug(args:Array, options:Object, outputId:String) : void
      {
         this.mA11yProbeDebug = this.mA11yProbeDebug + 1;
      }

      public function A11yStartupProbeLoaded(event:Event) : void
      {
         try { this.mA11yProbeStatus = "complete: " + String(this.mA11yProbeLoader["data"]).substr(0,100); }
         catch(e:Error) { this.mA11yProbeStatus = "complete, data error: " + e.message; }
      }

      public function A11yStartupProbeFailed(event:Event) : void
      {
         this.mA11yProbeStatus = String(event).substr(0,160);
      }

      public function A11yStartupProbeFrame(event:Event = null) : void
      {
         try
         {
            if(getTimer() < this.mA11yProbeNext) { return; }
            this.mA11yProbeNext = getTimer() + 5000;
            this.mA11yProbeFrames = this.mA11yProbeFrames + 1;
            if(this.mA11yProbeFrames <= 12 && this.mA11yProbeStatus.indexOf("ACK_V94") < 0)
            {
               try
               {
                  if(this.mA11yProbeLoader != null) { try { this.mA11yProbeLoader["close"](); } catch(closeError:Error) { } }
                  var loaderClass:Class = getDefinitionByName("flash.net.URLLoader") as Class;
                  var requestClass:Class = getDefinitionByName("flash.net.URLRequest") as Class;
                  this.mA11yProbeLoader = new loaderClass();
                  this.mA11yProbeLoader["addEventListener"]("complete",this.A11yStartupProbeLoaded);
                  this.mA11yProbeLoader["addEventListener"]("ioError",this.A11yStartupProbeFailed);
                  this.mA11yProbeLoader["addEventListener"]("securityError",this.A11yStartupProbeFailed);
                  this.mA11yProbeStatus = "request " + this.mA11yProbeFrames + " pending";
                  this.mA11yProbeLoader["load"](new requestClass("http://127.0.0.1:45991/a11y-startup-v94"));
               }
               catch(loadError:Error) { this.mA11yProbeStatus = "load error: " + loadError.message; }
            }
            this.mA11yProbeLabel.text = "STARTUP TRANSPORT V9.4: UI ticks " + this.mA11yProbeFrames + ", native debug " + this.mA11yProbeDebug +
               "\nLocal probe: " + this.mA11yProbeStatus;
         }
         catch(e:Error) { }
      }
