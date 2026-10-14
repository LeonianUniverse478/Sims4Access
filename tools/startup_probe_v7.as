      // ISOLATED DIAGNOSTIC ONLY. Never included in the normal package.
      protected var mA11yProbeLabel:TextField = null;
      protected var mA11yProbeNext:int = 0;
      protected var mA11yProbeFrames:int = 0;
      protected var mA11yProbeKeys:int = 0;
      protected var mA11yProbeDebug:int = 0;
      protected var mA11yProbeAck:Boolean = false;
      protected var mA11yProbeAction:Object = null;
      protected var mA11yProbeError:String = "";

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
            this.mA11yProbeLabel.width = 720;
            this.mA11yProbeLabel.height = 80;
            this.mA11yProbeLabel.x = 24;
            this.mA11yProbeLabel.y = 24;
            this.mTooltipsLayer.stage.addChild(this.mA11yProbeLabel);
            this.mTooltipsLayer.stage.addEventListener(Event.ENTER_FRAME,this.A11yStartupProbeFrame,false,0,true);
            CommunicationManager.AddMessageListenerByName("A11yStartupProbeAck",this.A11yStartupProbeReply,"A11yProbe");
            var debug:Object = getDefinitionByName("olympus.io.DebugCommands");
            debug["Register"]("ui.a11y.startup_probe",this.A11yStartupProbeDebug,"A11Y_STARTUP_REGISTRY_SENTINEL_V7","No arguments. Updates the probe badge only.");
            var actionClass:Object = getDefinitionByName("olympus.input.InputAction");
            var triggerClass:Object = getDefinitionByName("olympus.input.InputTrigger");
            var manager:Object = getDefinitionByName("olympus.io.InputActionManager");
            var action:Object = actionClass["WhenTriggered"](triggerClass["FromKeyBinding"](121,0));
            action["SetPriority"](1000000);
            action["AllowWhileModalOpen"](true);
            action["CallFunction"](this.A11yStartupProbeKey);
            manager["RegisterAction"](action);
            this.mA11yProbeAction = action;
         }
         catch(e:Error) { this.mA11yProbeError = e.message; }
      }

      public function A11yStartupProbeKey() : Boolean
      {
         this.mA11yProbeKeys = this.mA11yProbeKeys + 1;
         this.mA11yProbeNext = 0;
         return false;
      }

      public function A11yStartupProbeDebug(args:Array, options:Object, outputId:String) : void
      {
         this.mA11yProbeDebug = this.mA11yProbeDebug + 1;
         this.mA11yProbeNext = 0;
      }

      public function A11yStartupProbeReply(data:Object = null) : void
      {
         this.mA11yProbeAck = true;
      }

      public function A11yStartupProbeFrame(event:Event = null) : void
      {
         try
         {
            if(getTimer() < this.mA11yProbeNext) { return; }
            this.mA11yProbeNext = getTimer() + 5000;
            this.mA11yProbeFrames = this.mA11yProbeFrames + 1;
            this.mA11yProbeLabel.text = "STARTUP PROBE: ClassLibraryGamedata, UI " + this.mA11yProbeFrames +
               ", F10 " + this.mA11yProbeKeys + ", debug " + this.mA11yProbeDebug +
               "\nPython reply: " + this.mA11yProbeAck + ", keyboard configuration received: " + this.mA11yKeyboard +
               "\nSetup error: " + this.mA11yProbeError;
            CommunicationManager.PostServerCommand("a11y.startup_probe","flash_" + this.mA11yProbeFrames);
         }
         catch(e:Error) { }
      }
