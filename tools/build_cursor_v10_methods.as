      // V10: native client cursor. This is screen navigation, not lot-grid
      // placement. Every commit goes through EA's own active Build tool.
      protected var mA11yBuildCursor:Boolean = false;
      protected var mA11yBuildX:int = 0;
      protected var mA11yBuildY:int = 0;
      protected var mA11yBuildStep:int = 16;
      protected var mA11yBuildListeners:Boolean = false;
      protected var mA11yBuildMarker:Sprite = null;
      protected var mA11yBuildAimSerial:int = 0;
      protected var mA11yBuildAimZone:String = "";
      protected var mA11yBuildAimUntil:int = 0;
      protected var mA11yBuildAimFrames:int = 0;

      public function A11yBuildUnbind() : void
      {
         var marker:Sprite = this.mA11yBuildMarker;
         this.mA11yBuildMarker = null;
         this.mA11yBuildAimSerial = 0;
         try { if(marker != null) { CommunicationManager.CallGameService("UnbindDisplayObject",{"displayObject":marker}); } }
         catch(unbindError:Error) { }
         try { if(marker != null && marker.parent != null) { marker.parent.removeChild(marker); } }
         catch(removeError:Error) { }
      }

      public function A11yBuildEnable(bounds:Rectangle) : void
      {
         try
         {
            this.A11yBuildObserve();
            this.A11yClearFocus();
            this.mA11yScope = null;
            this.mA11yPendingScope = null;
            this.mA11yHudBrowsing = false;
            CommunicationManager.CallGameService("SetupVirtualCursor",{"enabled":true,"restraintLeft":bounds.left,"restraintTop":bounds.top,"restraintRight":bounds.right,"restraintBottom":bounds.bottom,"onConfirmDown":0,"onConfirmUp":0},true);
            this.mA11yBuildCursor = true;
         }
         catch(e:Error) { this.mA11yBuildCursor = false; }
      }

      public function A11yBuildAim(parts:Array) : void
      {
         var serial:int = 0;
         var x:Number = NaN;
         var y:Number = NaN;
         var z:Number = NaN;
         var level:Number = NaN;
         try
         {
            serial = int(parts[2]);
            this.A11yBuildDisable();
            if(parts.length != 8 || serial <= 0 || !this.mA11yKeyboard || this.A11yWorldHudMode() != 2 || this.A11yBuildBlocked()) { this.A11yBuildReply(serial,"blocked"); return; }
            x = Number(parts[3]); y = Number(parts[4]); z = Number(parts[5]); level = Number(parts[6]);
            if(!isFinite(x) || !isFinite(y) || !isFinite(z) || !isFinite(level) || int(level) != level || Math.abs(x) > 100000 || Math.abs(y) > 100000 || Math.abs(z) > 100000) { this.A11yBuildReply(serial,"aimfailed"); return; }
            if(String(CommunicationManager.CallGameService("BBGetCurrentZoneId",null,true)) != String(parts[7])) { this.A11yBuildReply(serial,"aimfailed"); return; }
            this.mA11yBuildMarker = new Sprite();
            this.mA11yBuildMarker.name = "A11yBuildProjection";
            this.mA11yBuildMarker.mouseEnabled = false;
            this.mA11yBuildMarker.mouseChildren = false;
            this.mA11yBuildMarker.alpha = 0;
            this.mA11yBuildMarker.x = -1000000;
            this.mA11yBuildMarker.y = -1000000;
            this.mTooltipsLayer.addChild(this.mA11yBuildMarker);
            this.mA11yBuildAimSerial = serial;
            this.mA11yBuildAimZone = String(parts[7]);
            this.mA11yBuildAimUntil = getTimer() + 1500;
            this.mA11yBuildAimFrames = 0;
            // Exact EA DisplayObjectUtils.BindDisplayObject payload, without
            // clamping. Native code projects worldOffset on subsequent frames.
            CommunicationManager.CallGameService("BindDisplayObject",{"displayObject":this.mA11yBuildMarker,"worldOffset":{"x":x,"y":y,"z":z},"screenOffset":{"x":0,"y":0}});
         }
         catch(e:Error) { this.A11yBuildUnbind(); this.A11yBuildReply(serial,"aimfailed"); }
      }

      public function A11yBuildProjectionFrame() : void
      {
         var point:Point = null;
         var bounds:Rectangle = null;
         var serial:int = this.mA11yBuildAimSerial;
         try
         {
            if(this.mA11yBuildMarker == null) { return; }
            this.mA11yBuildAimFrames++;
            if(!this.mA11yKeyboard || getTimer() > this.mA11yKeyboardLease || this.A11yWorldHudMode() != 2 || this.A11yBuildBlocked() || String(CommunicationManager.CallGameService("BBGetCurrentZoneId",null,true)) != this.mA11yBuildAimZone)
            {
               this.A11yBuildUnbind(); this.A11yBuildReply(serial,"aimfailed"); return;
            }
            // At least one complete native frame must have elapsed; a marker
            // whose sentinel never changes cannot be accepted as projected.
            if(this.mA11yBuildAimFrames < 2) { return; }
            if(getTimer() > this.mA11yBuildAimUntil) { this.A11yBuildUnbind(); this.A11yBuildReply(serial,"aimfailed"); return; }
            point = this.mA11yBuildMarker.localToGlobal(new Point(0,0));
            bounds = this.A11yBuildBounds();
            if(this.mA11yBuildMarker.visible && bounds != null && isFinite(point.x) && isFinite(point.y) && point.x >= bounds.left && point.x <= bounds.right && point.y >= bounds.top && point.y <= bounds.bottom)
            {
               this.mA11yBuildX = int(point.x);
               this.mA11yBuildY = int(point.y);
               this.A11yBuildUnbind();
               this.A11yBuildEnable(bounds);
               if(!this.mA11yBuildCursor) { this.A11yBuildReply(serial,"aimfailed"); return; }
               CommunicationManager.CallGameService("SetVirtualCursorPosition",{"x":this.mA11yBuildX,"y":this.mA11yBuildY},true);
               this.A11yBuildReply(serial,"aim"); return;
            }
         }
         catch(e:Error) { this.A11yBuildUnbind(); this.A11yBuildReply(serial,"aimfailed"); }
      }

      public function A11yBuildObserve() : void
      {
         try
         {
            if(this.mA11yBuildListeners) { return; }
            CommunicationManager.AddMessageListenerByName("BBShowProductTooltip",this.A11yBuildProduct,"A11yBuildCursor");
            CommunicationManager.AddMessageListenerByName("BBNotifyError",this.A11yBuildError,"A11yBuildCursor");
            this.mA11yBuildListeners = true;
         }
         catch(e:Error) { }
      }

      public function A11yBuildProduct(data:Object) : void
      {
         var cls:Class = null;
         var product:Object = null;
         if(!this.mA11yBuildCursor || data == null) { return; }
         try
         {
            if(!data["show"] || data["product"] == null)
            {
               CommunicationManager.PostServerCommand("a11y.buildinfo","clear|"); return;
            }
            cls = getDefinitionByName("gamedata.BuildBuy.shared.CatalogProduct") as Class;
            product = new cls(data["product"]);
            CommunicationManager.PostServerCommand("a11y.buildinfo","name|" + encodeURIComponent(String(product["Name"])));
         }
         catch(e:Error) { }
      }

      public function A11yBuildError(data:Object) : void
      {
         var cls:Class = null;
         var key:Object = null;
         if(!this.mA11yBuildCursor || data == null) { return; }
         try
         {
            cls = getDefinitionByName("olympus.localization.LocKey") as Class;
            key = new cls("hash" in data ? data : data["labelKey"]);
            CommunicationManager.PostServerCommand("a11y.buildinfo","error|" + encodeURIComponent(String(key.toString())));
         }
         catch(e:Error) { }
      }

      public function A11yBuildToolAllowed() : Boolean
      {
         var inspector:Object = null;
         try
         {
         inspector = this.A11yLoadedWidget("BuildBuyInspector");
         if(inspector == null) { return false; }
         // A keyboard place request must not accidentally run a previously
         // selected sledgehammer, eyedropper, redesign or whole-lot tool.
         if(inspector["btnSledgehammer"].Selected || inspector["btnEyedropper"].Selected || inspector["btnDesignTool"].Selected) { return false; }
         if(inspector["mcMoveToolPanel"]["btnMoveHouse"].Selected || inspector["mcMoveToolPanel"]["btnMoveLot"].Selected) { return false; }
         return true;
         }
         catch(e:Error) { }
         return false;
      }

      public function A11yBuildBlocked() : Boolean
      {
         var top:DisplayObject = null;
         var names:Array = ["BuildBuyProductCatalog","BuildBuyNavigation","BuildBuyInspector","BuildBuyInventory","BuildBuyMagalog"];
         var i:int = 0;
         try
         {
            if(this.A11yEditing() || this.A11yIsLive(this.mA11yManagedDialog) || this.A11yCurrentDropdown() != null) { return true; }
            top = this.A11yTopModalWidget();
            if(top == null) { return false; }
            // The native catalog can itself be registered as a modal widget;
            // it stays open below the placement viewport while using a tool.
            while(i < names.length)
            {
               if(top == this.A11yLoadedWidget(String(names[i]))) { return false; }
               i++;
            }
         }
         catch(e:Error) { }
         return true;
      }

      public function A11yBuildReply(serial:int, result:String) : void
      {
         try
         {
         CommunicationManager.PostServerCommand("a11y.buildstate",serial.toString() + "|" + (this.mA11yBuildCursor ? "1" : "0") + "|" + result + "|" + this.mA11yBuildX.toString() + "|" + this.mA11yBuildY.toString() + "|" + this.mA11yBuildStep.toString());
         }
         catch(e:Error) { }
      }

      public function A11yBuildDisable() : void
      {
         this.A11yBuildUnbind();
         if(!this.mA11yBuildCursor) { return; }
         this.mA11yBuildCursor = false;
         try
         {
         CommunicationManager.CallGameService("SetupVirtualCursor",{"enabled":false,"restraintLeft":-1,"restraintTop":-1,"restraintRight":-1,"restraintBottom":-1,"onConfirmDown":0,"onConfirmUp":0},true);
         }
         catch(e:Error) { }
      }

      public function A11yBuildFrame() : void
      {
         try
         {
         this.A11yBuildProjectionFrame();
         if(this.mA11yBuildCursor && (!this.mA11yKeyboard || getTimer() > this.mA11yKeyboardLease || this.A11yWorldHudMode() != 2 || this.A11yBuildBlocked()))
         {
            this.A11yBuildDisable();
            this.A11yBuildReply(0,"off");
         }
         }
         catch(e:Error) { this.A11yBuildDisable(); }
      }

      public function A11yBuildBounds() : Rectangle
      {
         try
         {
         var api:Object = getDefinitionByName("olympus.gamepad.LayoutAPI");
         var width:Number = Number(api["StageWidth"]);
         var height:Number = Number(api["StageHeight"]);
         var bottom:Number = Number(CommunicationManager.CallUIService("GetNavigationUpperBound"));
         // Exclude the Build toolbar and native catalog using EA's bound.
         if(isNaN(bottom) || bottom < 160 || bottom > height - 8) { bottom = height - 120; }
         return new Rectangle(8,80,Math.max(1,width - 16),Math.max(1,bottom - 88));
         }
         catch(e:Error) { }
         return null;
      }

      public function A11yBuildCommand(action:String, serial:int) : void
      {
         var bounds:Rectangle = null;
         var input:Object = null;
         var dx:int = 0;
         var dy:int = 0;
         var inspector:Object = null;
         try
         {
            if(action == "off") { this.A11yBuildDisable(); this.A11yBuildReply(serial,"off"); return; }
            if(this.mA11yBuildMarker != null) { this.A11yBuildUnbind(); }
            if(this.A11yWorldHudMode() != 2 || !this.mA11yKeyboard) { this.A11yBuildDisable(); this.A11yBuildReply(serial,"unavailable"); return; }
            if(this.A11yBuildBlocked()) { this.A11yBuildDisable(); this.A11yBuildReply(serial,"blocked"); return; }
            if(action == "undo" || action == "redo")
            {
               inspector = this.A11yLoadedWidget("BuildBuyInspector");
               if(inspector == null || !inspector[action == "undo" ? "btnUndo" : "btnRedo"].enabled) { this.A11yBuildReply(serial,"nohistory"); return; }
               CommunicationManager.CallGameService("BBOpCommand",action);
               CommunicationManager.SendUIMessage("BBUndoRedo");
               this.A11yBuildReply(serial,action); return;
            }
            bounds = this.A11yBuildBounds();
            if(action == "on")
            {
               input = getDefinitionByName("olympus.utils.InputUtils");
               this.mA11yBuildX = int(input["sMouseX"]);
               this.mA11yBuildY = int(input["sMouseY"]);
               this.A11yBuildEnable(bounds);
            }
            if(!this.mA11yBuildCursor) { this.A11yBuildReply(serial,"unavailable"); return; }
            if(action == "cancel")
            {
               CommunicationManager.CallGameService("BBCancelUserTool");
               CommunicationManager.SendUIMessage("BBInspectorHideMoveToolPanel");
            }
            else if(action == "rotateleft" || action == "rotateright")
            {
               CommunicationManager.CallGameService("BBRotateSelectedObject",{"value":action == "rotateleft" ? -1 : 1});
            }
            else if(action == "click")
            {
               if(!this.A11yBuildToolAllowed()) { this.A11yBuildReply(serial,"toolblocked"); return; }
               this.mA11yBuildX = int(Math.max(bounds.left,Math.min(bounds.right,this.mA11yBuildX)));
               this.mA11yBuildY = int(Math.max(bounds.top,Math.min(bounds.bottom,this.mA11yBuildY)));
               CommunicationManager.CallGameService("SetVirtualCursorPosition",{"x":this.mA11yBuildX,"y":this.mA11yBuildY},true);
               CommunicationManager.CallGameService("BBGamepadPlaceMultiple",false);
               CommunicationManager.CallGameService("SendVirtualCursorClick");
            }
            else
            {
               if(action == "fine") { this.mA11yBuildStep = 4; }
               else if(action == "coarse") { this.mA11yBuildStep = this.mA11yBuildStep == 64 ? 16 : 64; }
               else if(action == "left") { dx = -this.mA11yBuildStep; }
               else if(action == "right") { dx = this.mA11yBuildStep; }
               else if(action == "up") { dy = -this.mA11yBuildStep; }
               else if(action == "down") { dy = this.mA11yBuildStep; }
               else if(action == "center") { this.mA11yBuildX = int(bounds.x + bounds.width / 2); this.mA11yBuildY = int(bounds.y + bounds.height / 2); }
               this.mA11yBuildX = int(Math.max(bounds.left,Math.min(bounds.right,this.mA11yBuildX + dx)));
               this.mA11yBuildY = int(Math.max(bounds.top,Math.min(bounds.bottom,this.mA11yBuildY + dy)));
               CommunicationManager.CallGameService("SetVirtualCursorPosition",{"x":this.mA11yBuildX,"y":this.mA11yBuildY},true);
               if(dx != 0 || dy != 0) { action = "move"; }
            }
            this.A11yBuildReply(serial,action);
         }
         catch(e:Error)
         {
            this.A11yBuildDisable();
            this.A11yBuildReply(serial,"unavailable");
         }
      }
