      // CASStories creates its own dialog as a direct display child, outside
      // DialogManager. Read that visible native child; never construct, move,
      // bind, hide or bypass the native story flow here.
      public function A11yCASStoryScope() : DisplayObject
      {
         var root:DisplayObjectContainer = null;
         var child:DisplayObject = null;
         var i:int = 0;
         try
         {
            root = this.A11yLoadedWidget("CASStories") as DisplayObjectContainer;
            if(!this.A11yIsLive(root)) { return null; }
            i = root.numChildren - 1;
            while(i >= 0)
            {
               child = root.getChildAt(i);
               if(getQualifiedClassName(child) == "widgets.CAS.Stories::CASStoriesDialog" && this.A11yIsLive(child)) { return child; }
               i = i - 1;
            }
         }
         catch(e:Error) { }
         return null;
      }

      // UIManager calls TooltipManager.Clear while changing game state.
      // Drop only our references/listeners before EA unloads its controls.
      // Do not synthesize mouse-out events into a departing widget's handlers.
      public function A11yResetGameState() : void
      {
         this.A11yFenceOpeningInput();
         this.A11yCancelIndex();
         this.A11yWatchFocused(this.mA11yFocused,null);
         if(this.mTooltipsLayer != null)
         {
            this.mTooltipsLayer.removeEventListener(Event.ENTER_FRAME,this.A11yScopeFrame);
            this.mTooltipsLayer.removeEventListener(Event.ENTER_FRAME,this.A11yScrollFrame);
         }
         if(this.mA11yBuildCursor || this.mA11yBuildMarker != null) { this.A11yBuildDisable(); }
         this.A11yKeyProbeOff();
         this.A11yClearRing();
         this.mA11yFocused = null;
         this.mA11yLastWidget = null;
         this.mA11yScope = null;
         this.mA11yPendingScope = null;
         this.mA11yManagedDialog = null;
         this.mA11yModalWidget = null;
         this.mA11yActiveModalRoot = null;
         this.mA11yStatusScope = null;
         this.mA11yHudRoot = null;
         this.mA11yHudButton = null;
         this.mA11yHudBrowsing = false;
         this.mA11yHudMode = 0;
         this.mA11yScopeHistory.length = 0;
         this.mA11yNavQueue.length = 0;
         this.mA11yList = null;
         this.mA11yListRoot = null;
         this.mA11yLogicalList = null;
         this.mA11yLogicalIndex = -1;
         this.mA11yReturnList = null;
         this.mA11yReturnIndex = -1;
         this.mA11yDropdown = null;
         this.mA11yDropdownExtension = null;
         this.mA11yDropdownButton = null;
         this.mA11yResumeFocus = null;
         this.mA11yFocusPending = null;
         this.mA11yScrollAnchor = null;
         this.mA11yPrevList = null;
         this.mA11yScrollDir = 0;
         this.mA11yScopeTries = 0;
         this.mA11yActivating = false;
         this.mA11yOpening = false;
         this.mA11yGuardHeld = new Object();
         this.mA11yNativeTabDirection = 0;
         this.mA11yListMemory = new Dictionary(true);
         this.mA11yGroupMemory = new Dictionary(true);
         this.mA11yMotiveLinks = new Dictionary(true);
         this.mA11yModalReported = "";
         this.mA11yOwnerReported = "";
         this.mA11yLast = "";
      }
