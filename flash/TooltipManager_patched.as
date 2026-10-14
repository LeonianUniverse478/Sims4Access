package olympus.core
{
   import flash.display.DisplayObject;
   import flash.display.DisplayObjectContainer;
   import flash.display.MovieClip;
   import flash.display.SimpleButton;
   import flash.display.Sprite;
   import flash.display.Stage;
   import flash.events.Event;
   import flash.events.KeyboardEvent;
   import flash.events.MouseEvent;
   import flash.external.ExternalInterface;
   import flash.geom.Point;
   import flash.geom.Rectangle;
   import flash.text.TextField;
   import flash.text.TextFormat;
   import flash.utils.Dictionary;
   import flash.utils.getDefinitionByName;
   import flash.utils.getQualifiedClassName;
   import flash.utils.getTimer;
   import olympus.core.tooltip.Tooltip;
   import olympus.gui.buttons.Button;
   import olympus.interfaces.ITooltip;
   import olympus.io.CommunicationManager;
   import scaleform.gfx.MouseEventEx;

   // own-alpha filtering active
   public class TooltipManager
   {

      protected static var sInstance:TooltipManager;

      protected var mTooltips:Object;

      protected var mTooltipsLayer:Layer;

      protected var mDefaultTooltip:ITooltip;

      protected var mbDisabled:Boolean;

      protected var mA11yLast:String = "";

      protected var mA11yLastTime:int = 0;

      protected var mA11yWindowStart:int = 0;

      protected var mA11yWindowCount:int = 0;

      protected var mA11yMarked:Boolean = false;

      protected var mA11ySentAny:Boolean = false;

      protected var mA11yStageHooked:Boolean = false;

      protected var mA11yLastWidget:DisplayObject = null;

      protected var mA11yFocused:DisplayObject = null;

      protected var mA11yCASInput:DisplayObject = null;

      protected var mA11yRing:Sprite = null;
      protected var mA11yRingBounds:Rectangle = null;

      protected var mA11yCaption:Sprite = null;

      protected var mA11yCaptionText:TextField = null;

      protected var mA11yCaptionUntil:int = 0;

      protected var mA11yScope:DisplayObject = null;

      protected var mA11yPendingScope:DisplayObject = null;

      protected var mA11yAutoFocus:Boolean = false;

      protected var mA11yIdxLayout:Object = null;

      protected var mA11yIdxList:Object = null;

      protected var mA11yIdxTarget:int = -1;

      protected var mA11yIdxTries:int = 0;

      protected var mA11yIdxDir:int = 0;

      protected var mA11yScopeTries:int = 0;

      protected var mA11yActivating:Boolean = false;

      protected var mA11yList:Array = null;

      protected var mA11yListRoot:DisplayObject = null;

      protected var mA11yEdge:int = 0;

      protected var mA11yScrollDir:int = 0;

      protected var mA11yScrollTries:int = 0;

      protected var mA11yScrollAnchor:DisplayObject = null;

      protected var mA11yPrevList:Array = null;

      protected var mA11yScopeHistory:Array = new Array();
      protected var mA11yManagedDialog:DisplayObject = null;
      protected var mA11yModalWidget:DisplayObject = null;
      protected var mA11yActiveModalRoot:DisplayObject = null;
      protected var mA11yLayoutManager:Object = null;
      protected var mA11yDialogManager:Object = null;
      protected var mA11yModalReported:String = "";
      protected var mA11yBlockingReported:String = "";
      protected var mA11yNavQueue:Array = new Array();
      protected var mA11yLogicalList:Object = null;
      protected var mA11yLogicalIndex:int = -1;

      // Native key actions consume game input; Python supplies deliberate
      // press/repeat/release messages. No controller-mode changes or EXE hooks.
      protected var mA11yKeyboard:Boolean = false;
      protected var mA11ySimplifiedMenus:Boolean = true;
      protected var mA11yPointerSpeechHeld:Boolean = false;
      protected var mA11yPointerSpeechX:Number = 0;
      protected var mA11yPointerSpeechY:Number = 0;
      protected var mA11yNativeActions:Array = new Array();
      protected var mA11yGuardHeld:Object = new Object();
      protected var mA11yNativeTabDirection:int = 0;
      protected var mA11yNativeTabTime:int = 0;
      protected var mA11yHudRoot:DisplayObject = null;
      protected var mA11yHudButton:DisplayObject = null;
      protected var mA11yHudBrowsing:Boolean = false;
      protected var mA11yHudMode:int = 0;
      protected var mA11yScopeReadyAt:int = 0;
      protected var mA11yListMemory:Dictionary = new Dictionary(true);
      protected var mA11yFocusDue:int = 0;
      protected var mA11yFocusPending:DisplayObject = null;
      protected var mA11yStatusScope:DisplayObject = null;
      protected var mA11yPhoneOwner:String = "";
      protected var mA11yPhoneUntil:int = 0;
      // TS4 Access Plus catalog bridge (merged 2026-10-08): the products of the
      // last listed catalog category, and whether build errors are forwarded.
      protected var mA11yPlusProducts:Array = new Array();
      protected var mA11yPlusListening:Boolean = false;
      // Guided New Game (2026-10-13): the step the guide is on during a new
      // family's CAS ("" waiting, "skip" not offered here, "open" a guide
      // dialog is up, "done" finished or declined), when CAS became ready,
      // and the guide dialog's id so its callbacks ignore stale dialogs.
      protected var mA11yGuideState:String = "";
      protected var mA11yGuideReadyAt:int = 0;
      protected var mA11yGuideCheckAt:int = 0;
      protected var mA11yGuideDialogId:String = "";
      protected var mA11yGuideSerial:int = 0;
      protected var mA11yGuideEditSeen:Boolean = false;
      protected var mA11yGuideEditAt:int = 0;
      protected var mA11yGuideList:Array = new Array();
      protected var mA11yGuideAspiration:String = "";
      protected var mA11yGuideTraitsOpen:Boolean = false;
      protected var mA11yGuidePhase:String = "";
      protected var mA11yGuidePhaseAt:int = 0;
      protected var mA11yGuideMapAt:int = 0;
      protected var mA11yGuideHousehold:String = "";
      protected var mA11yGuideRegion:String = "";
      protected var mA11yGuideLot:Object = null;
      protected var mA11yGuideFurnish:int = -1;
      protected var mA11yGuideFresh:Object = new Object();
      protected var mA11yGuideNames:Object = new Object();
      protected var mA11yGuideNewSim:Boolean = false;
      protected var mA11yGuideAddFrom:String = "";
      protected var mA11yKeyboardLease:int = 0;
      protected var mA11yReturnList:Object = null;
      protected var mA11yReturnIndex:int = -1;
      protected var mA11yOwnerReported:String = "";
      protected var mA11yGroupMemory:Dictionary = new Dictionary(true);
      protected var mA11yDropdown:DisplayObject = null;
      protected var mA11yDropdownExtension:Object = null;
      protected var mA11yDropdownButton:DisplayObject = null;
      protected var mA11yResumeFocus:DisplayObject = null;
      protected var mA11yOpening:Boolean = false;
      protected var mA11ySilentMood:String = "";
      protected var mA11yInvCell:DisplayObject = null;
      // The Build catalog widget Escape released: it stays open for EA (and
      // keeps the chosen product) but does not own the keys until Tab.
      protected var mA11yCatalogReleased:DisplayObject = null;
      // The Build cursor (Python grid, Build mode) owns plain keys while on.
      protected var mA11yBuildGridOn:Boolean = false;
      protected var mA11yBuildGridReported:String = "";
      protected var mA11yMotiveLinks:Dictionary = new Dictionary(true);

      // BEGIN A11Y V10 NATIVE BUILD CURSOR
      // V10: native client cursor. This is screen navigation, not lot-grid
      // placement. Every commit goes through EA's own active Build tool.
      protected var mA11yBuildCursor:Boolean = false;
      protected var mA11yBuildControls:Boolean = false;
      // Scanner mode: bare keys browse the Python scanner while no other
      // owner holds input. Python sends the mode; this copy reports whether
      // it currently owns the keys (a11y.scannerowner) and consumes them.
      protected var mA11yScannerMode:Boolean = false;
      protected var mA11yScannerOwnerReported:String = "";
      protected var mA11yScannerLiveReported:String = "";
      protected var mA11yFirstPersonKnown:Boolean = false;
      protected var mA11yFirstPerson:Boolean = false;
      protected var mA11yFirstPersonFence:int = 0;
      protected var mA11yBuildPositionKnown:Boolean = false;
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
         if(!this.mA11yBuildControls) { return; }
         try
         {
            this.A11yBuildObserve();
            this.A11yClearFocus();
            this.mA11yScope = null;
            this.mA11yPendingScope = null;
            this.mA11yHudBrowsing = false;
            this.A11yBuildSnapshot("enable-before");
            var enabledResult:Object = CommunicationManager.CallGameService("SetupVirtualCursor",{"enabled":true,"restraintLeft":bounds.left,"restraintTop":bounds.top,"restraintRight":bounds.right,"restraintBottom":bounds.bottom,"onConfirmDown":0,"onConfirmUp":0},true);
            this.A11yBuildLog("enable native return=" + String(enabledResult));
            this.mA11yBuildCursor = true;
            this.mA11yBuildPositionKnown = true;
            this.A11yBuildSnapshot("enable-after");
         }
         catch(e:Error) { this.mA11yBuildCursor = false; this.A11yBuildLog("enable error=" + e.name + ":" + e.message); }
      }

      public function A11yBuildSnapshot(label:String) : void
      {
         var info:String = label + " owned=" + this.mA11yBuildCursor;
         var input:Object = null;
         try
         {
            input = getDefinitionByName("olympus.utils.SystemUtils");
            info += " console=" + input["IsConsole"] + " controller=" + input["UsingController"] + " mouseKeyboard=" + input["UsingMouseKeyboard"];
         }
         catch(systemError:Error) { info += " systemError=" + systemError.message; }
         try
         {
            input = getDefinitionByName("olympus.utils.InputUtils");
            info += " input=" + input["sMouseX"] + "," + input["sMouseY"];
         }
         catch(inputError:Error) { info += " inputError=" + inputError.message; }
         try
         {
            if(this.mTooltipsLayer != null && this.mTooltipsLayer.stage != null)
            {
               info += " stage=" + this.mTooltipsLayer.stage.mouseX + "," + this.mTooltipsLayer.stage.mouseY;
            }
         }
         catch(stageError:Error) { info += " stageError=" + stageError.message; }
         this.A11yBuildLog(info.substr(0,390));
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
            if(!this.mA11yBuildControls) { this.A11yBuildReply(serial,"unavailable"); return; }
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

      protected var mA11yBuildProduct:Object = null;            // last BBProductSelected payload's product
      protected var mA11yBuildProductLost:Boolean = false;      // cancelled by a modal while remembered
      protected var mA11yBuildProductModals:int = 0;            // SetModalVisible balance seen here
      protected var mA11yBuildProductClosedAt:int = 0;          // getTimer when the balance last reached 0
      protected var mA11yBuildProductDropPending:Boolean = false; // tool/mode change seen with no modal open, not yet finalized
      protected var mA11yBuildProductObserved:Boolean = false;
      public static const A11Y_PRODUCT_RESTORE_WINDOW:int = 5000;

      public function A11yBuildLog(message:String) : void
      {
         try { this.A11yPostToPython("a11y.buildlog",encodeURIComponent(message)); }
         catch(logError:Error) { }
      }

      public function A11yBuildProductObserve() : void
      {
         if(!this.mA11yBuildControls) { return; }
         try
         {
            if(this.mA11yBuildProductObserved) { return; }
            CommunicationManager.AddMessageListenerByName("BBProductSelected",this.A11yBuildProductSelected,"A11yBuildCursor");
            CommunicationManager.AddMessageListenerByName("SetModalVisible",this.A11yBuildProductModal,"A11yBuildCursor");
            CommunicationManager.AddMessageListenerByName("BBToggleBuildSelect",this.A11yBuildProductDropped,"A11yBuildCursor");
            CommunicationManager.AddMessageListenerByName("BBActionModeChanged",this.A11yBuildProductDropped,"A11yBuildCursor");
            this.mA11yBuildProductObserved = true;
            this.A11yBuildLog("observe registered");
         }
         catch(e:Error) { }
      }

      public function A11yBuildProductOrdinary(product:Object) : Boolean
      {
         // Positive classifier: the catalog's object product class itself
         // (rooms, styles and patterns are other classes and never reach
         // BBProductSelected through CatalogProduct.Select), a resource key
         // usable by BBSelectProduct, and no sculpt or pond tool product.
         try
         {
            if(product == null || product["resourceKey"] == null) { return false; }
            if(getQualifiedClassName(product) != "gamedata.BuildBuy.shared::CatalogProduct") { return false; }
            if(int(product["sculptType"]) != 0 || int(product["pondType"]) != 0) { return false; }
            return true;
         }
         catch(e:Error) { }
         return false;
      }

      public function A11yBuildProductSelected(data:Object) : void
      {
         if(!this.mA11yBuildControls) { return; }
         try
         {
            var product:Object = data == null ? null : data["product"];
            this.A11yBuildLog("selected class=" + (product == null ? "null" : getQualifiedClassName(product)) + " ordinary=" + this.A11yBuildProductOrdinary(product));
            if(!this.A11yBuildProductOrdinary(product)) { this.A11yPostToPython("a11y.buildproduct","0|"); this.A11yBuildProductForget(); return; }
            this.mA11yBuildProduct = product;
            this.A11yPostToPython("a11y.buildproduct",String(product["resourceKey"]["instance"]) + "|" + encodeURIComponent(String(product["Name"])));
            this.mA11yBuildProductLost = false;
            this.mA11yBuildProductDropPending = false;
            this.mA11yBuildProductClosedAt = 0;
         }
         catch(e:Error) { this.A11yBuildProductForget(); }
      }

      public function A11yBuildHandDrop(serial:String) : void
      {
         var result:String = "denied";
         try
         {
            if(this.mA11yBuildControls && this.mA11yKeyboard && getTimer() <= this.mA11yKeyboardLease && this.A11yWorldHudMode() == 2 && !this.A11yBuildBlocked() && this.A11yBuildToolAllowed())
            {
               this.A11yBuildProductForget();
               CommunicationManager.CallGameService("BBCancelUserTool");
               CommunicationManager.SendUIMessage("BBInspectorHideMoveToolPanel");
               result = "ok";
            }
         }
         catch(e:Error) { result = "denied"; }
         this.A11yPostToPython("a11y.buildhand",serial + "|" + result);
      }

      public function A11yBuildProductModal(data:Object) : void
      {
         if(!this.mA11yBuildControls) { return; }
         // Keep our own modal balance. Opening the first modal is when EA's
         // inspector cancels the held product; closing the last one starts
         // the short window in which an explicit menu action may restore it.
         try
         {
            this.A11yBuildLog("modal=" + Boolean(data) + " balance=" + this.mA11yBuildProductModals + " editing=" + this.A11yEditing());
            if(Boolean(data))
            {
               this.mA11yBuildProductModals = this.mA11yBuildProductModals + 1;
               if(this.mA11yBuildProduct == null || !this.mA11yKeyboard) { return; }
               // A tool/mode change still pending from this same dispatch was
               // the inspector's own cancellation (its listener ran first).
               this.mA11yBuildProductDropPending = false;
               this.mA11yBuildProductLost = true;
               return;
            }
            if(this.mA11yBuildProductModals > 0) { this.mA11yBuildProductModals = this.mA11yBuildProductModals - 1; }
            if(this.mA11yBuildProductModals == 0) { this.mA11yBuildProductClosedAt = getTimer(); }
         }
         catch(e:Error) { this.A11yBuildProductForget(); }
      }

      public function A11yBuildProductDropped(data:Object) : void
      {
         if(!this.mA11yBuildControls) { return; }
         this.A11yBuildLog("dropped balance=" + this.mA11yBuildProductModals + " editing=" + this.A11yEditing() + " product=" + (this.mA11yBuildProduct != null));
         // While a modal is open, tool/mode changes are EA reacting to its own
         // cancellation. With none open they are the player's unless a modal
         // opens before the next frame (see A11yBuildProductFrame).
         if(this.mA11yBuildProductModals > 0) { return; }
         if(this.mA11yBuildProduct == null) { return; }
         this.mA11yBuildProductDropPending = true;
      }

      public function A11yBuildProductFrame() : void
      {
         // Finalize a tool/mode change nobody claimed: the player let go.
         if(this.mA11yBuildProductDropPending) { this.A11yBuildLog("frame forget"); this.A11yBuildProductForget(); }
      }

      public function A11yBuildProductForget() : void
      {
         if(this.mA11yBuildProduct != null) { this.A11yBuildLog("forget product"); }
         this.mA11yBuildProduct = null;
         this.mA11yBuildProductLost = false;
         this.mA11yBuildProductDropPending = false;
         this.mA11yBuildProductClosedAt = 0;
      }

      public function A11yBuildProductRestore() : Boolean
      {
         if(!this.mA11yBuildControls) { return false; }
         // Once, right after an explicit menu action re-enabled the cursor:
         // put the remembered product back in hand with the catalog's own call
         // (CatalogProduct.Select -> BBSelectProduct + BBProductSelected).
         var product:Object = this.mA11yBuildProduct;
         var now:int = getTimer();
         this.A11yBuildLog("restore product=" + (product != null) + " lost=" + this.mA11yBuildProductLost + " modals=" + this.mA11yBuildProductModals + " pending=" + this.mA11yBuildProductDropPending + " closed=" + this.mA11yBuildProductClosedAt + " now=" + now + " cursor=" + this.mA11yBuildCursor);
         if(product == null || !this.mA11yBuildProductLost) { return false; }
         if(this.mA11yBuildProductModals > 0) { return false; }             // a modal is still up: keep the memory
         if(this.mA11yBuildProductDropPending) { this.A11yBuildProductForget(); return false; }   // the player acted after the modal
         if(this.mA11yBuildProductClosedAt == 0 || now - this.mA11yBuildProductClosedAt > A11Y_PRODUCT_RESTORE_WINDOW) { this.A11yBuildProductForget(); return false; }
         this.mA11yBuildProductLost = false;
         this.mA11yBuildProductClosedAt = 0;
         try
         {
            if(!this.mA11yBuildCursor || this.A11yBuildBlocked()) { return false; }
            product["Select"](null,null,0,2,int(product["stateIndex"]));
            this.A11yBuildLog("restore Select returned");
            return true;
         }
         catch(e:Error) { this.A11yBuildLog("restore failed: " + e.message); this.A11yBuildProductForget(); }
         return false;
      }


      public function A11yBuildObserve() : void
      {
         if(!this.mA11yBuildControls) { return; }
         try
         {
            this.A11yBuildProductObserve();
            if(this.mA11yBuildListeners) { return; }
            CommunicationManager.AddMessageListenerByName("BBShowProductTooltip",this.A11yBuildProduct,"A11yBuildCursor");
            CommunicationManager.AddMessageListenerByName("BBNotifyError",this.A11yBuildError,"A11yBuildCursor");
            CommunicationManager.AddMessageListenerByName("UsingControllerToggled",this.A11yBuildUsingControllerToggled,"A11yBuildCursor");
            CommunicationManager.AddMessageListenerByName("CursorModeToggled",this.A11yBuildCursorModeToggled,"A11yBuildCursor");
            this.mA11yBuildListeners = true;
         }
         catch(e:Error) { }
      }

      // Keep observing after disable so delayed engine mode changes are visible.
      // UsingControllerToggled has no payload; CursorModeToggled carries isCursorMode.
      public function A11yBuildUsingControllerToggled(data:Object = null) : void
      {
         if(!this.mA11yBuildControls) { return; }
         try { this.A11yBuildLog(("UsingControllerToggled payload=" + String(data)).substr(0,390)); }
         catch(e:Error) { this.A11yBuildLog("UsingControllerToggled payloadError=" + e.message); }
         this.A11yBuildSnapshot("UsingControllerToggled");
      }

      public function A11yBuildCursorModeToggled(data:Object = null) : void
      {
         if(!this.mA11yBuildControls) { return; }
         try { this.A11yBuildLog(("CursorModeToggled payload=" + String(data) + " isCursorMode=" + (data == null ? "null" : (String(data["isCursorMode"])))).substr(0,390)); }
         catch(e:Error) { this.A11yBuildLog("CursorModeToggled payloadError=" + e.message); }
         this.A11yBuildSnapshot("CursorModeToggled");
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
               this.A11yPostToPython("a11y.buildinfo","clear|"); return;
            }
            cls = getDefinitionByName("gamedata.BuildBuy.shared.CatalogProduct") as Class;
            product = new cls(data["product"]);
            this.A11yPostToPython("a11y.buildinfo","name|" + encodeURIComponent(String(product["Name"])));
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
            this.A11yPostToPython("a11y.buildinfo","error|" + encodeURIComponent(String(key.toString())));
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

      // Escape in the Build catalog: release the keys, keep EA's catalog and
      // the chosen product exactly as they are (no EA call), so the lot grid
      // chords reach the world. Python announces the chosen object.
      public function A11yIsBuildBuy(item:DisplayObject) : Boolean
      {
         var names:Array = ["BuildBuyProductCatalog","BuildBuyNavigation","BuildBuyInspector","BuildBuyInventory","BuildBuyMagalog"];
         var i:int = 0;
         try
         {
            if(item == null) { return false; }
            if(getQualifiedClassName(item).indexOf("BuildBuy") >= 0) { return true; }
            while(i < names.length)
            {
               if(item == this.A11yLoadedWidget(String(names[i]))) { return true; }
               i = i + 1;
            }
         }
         catch(e:Error) { }
         return false;
      }

      // The Build/Buy widget that owns the keys now, whichever way: as the
      // modal root, or reached by Tab (HUD browsing) with focus inside it.
      public function A11yBuildCatalogOwner() : DisplayObject
      {
         var node:DisplayObject = null;
         var found:DisplayObject = null;
         var depth:int = 0;
         try
         {
            if(this.A11yWorldHudMode() != 2) { return null; }
            if(this.mA11yActiveModalRoot != null && this.A11yIsLive(this.mA11yActiveModalRoot) && this.A11yIsBuildBuy(this.mA11yActiveModalRoot)) { return this.mA11yActiveModalRoot; }
            if(this.mA11yActiveModalRoot != null && this.A11yIsLive(this.mA11yActiveModalRoot)) { return null; }
            if(!this.mA11yHudBrowsing && this.mA11yScope == null) { return null; }
            node = this.mA11yFocused;
            while(node != null && depth < 40)
            {
               if(this.A11yIsBuildBuy(node)) { found = node; }
               node = node.parent;
               depth = depth + 1;
            }
         }
         catch(e:Error) { }
         return found;
      }

      // Escape in the Build catalog, or the Build cursor starting: release the
      // keys, keep EA's catalog and the chosen product exactly as they are (no
      // EA call), so the cursor's keys reach the world. Python announces.
      public function A11yReleaseBuildCatalog(announce:Boolean = true) : Boolean
      {
         var owner:DisplayObject = null;
         try
         {
            owner = this.A11yBuildCatalogOwner();
            if(owner == null) { return false; }
            this.mA11yCatalogReleased = this.mA11yModalWidget != null && this.A11yIsLive(this.mA11yModalWidget) && this.A11yIsBuildBuy(this.mA11yModalWidget) ? this.mA11yModalWidget : owner;
            this.mA11yActiveModalRoot = null;
            this.mA11yHudBrowsing = false;
            this.A11yCancelIndex();
            this.A11yClearFocus();
            this.mA11yScope = null;
            this.mA11yScopeHistory.length = 0;
            if(announce) { this.A11yPostToPython("a11y.catalogleft","1"); }
            return true;
         }
         catch(e:Error) { }
         return false;
      }

      public function A11yBuildGridOwner() : Boolean
      {
         try
         {
            if(!this.mA11yBuildGridOn || !this.mA11yKeyboard || getTimer() > this.mA11yKeyboardLease) { return false; }
            if(this.mA11yStartupActive || this.A11yWorldHudMode() != 2 || this.A11yEditing()) { return false; }
            if(this.mA11yBuildCursor || this.mA11yHudBrowsing || this.mA11yStatusScope != null) { return false; }
            if(this.A11yIsLive(this.mA11yActiveModalRoot)) { return false; }
            if(this.A11yIsModalScope(this.mA11yScope) || this.A11yIsModalScope(this.mA11yPendingScope)) { return false; }
            return true;
         }
         catch(e:Error) { }
         return false;
      }

      // Python turned the Build cursor on: a catalog still owning the keys
      // lets go silently (EA keeps the chosen product); Tab returns to it.
      public function A11yBuildGridOnMsg(param1:Object = null) : void
      {
         try
         {
            this.mA11yBuildGridOn = true;
            this.A11yReleaseBuildCatalog(false);
         }
         catch(e:Error) { }
      }

      public function A11yBuildGridOffMsg(param1:Object = null) : void
      {
         this.mA11yBuildGridOn = false;
      }

      public function A11yReturnToCatalog() : Boolean
      {
         var modal:Boolean = false;
         if(this.mA11yCatalogReleased == null) { return false; }
         modal = this.mA11yCatalogReleased == this.mA11yModalWidget;
         this.mA11yCatalogReleased = null;
         // A modal catalog: the next frame focuses it. One reached by Tab:
         // this Tab enters the Build panels as usual.
         return modal;
      }

      public function A11yBuildReply(serial:int, result:String) : void
      {
         try
         {
         this.A11yPostToPython("a11y.buildstate",serial.toString() + "|" + (this.mA11yBuildCursor ? "1" : "0") + "|" + result + "|" + this.mA11yBuildX.toString() + "|" + this.mA11yBuildY.toString() + "|" + this.mA11yBuildStep.toString());
         }
         catch(e:Error) { }
      }

      public function A11yBuildDisable(force:Boolean = false) : void
      {
         this.A11yBuildUnbind();
         if(!this.mA11yBuildCursor && !force) { return; }
         this.A11yBuildSnapshot("disable-before force=" + force);
         this.mA11yBuildCursor = false;
         try
         {
         var disabledResult:Object = CommunicationManager.CallGameService("SetupVirtualCursor",{"enabled":false,"restraintLeft":-1,"restraintTop":-1,"restraintRight":-1,"restraintBottom":-1,"onConfirmDown":0,"onConfirmUp":0},true);
         this.A11yBuildLog("disable native return=" + String(disabledResult));
         }
         catch(e:Error) { this.A11yBuildLog("disable error=" + e.name + ":" + e.message); }
         // Candidate cleanup: EA's VirtualCursorInputAdapter sends a -1,-1
         // position (FireMouseMoveEvent) when it enables its cursor, which
         // hands the engine pointer back to the real mouse. Sent here after
         // disabling because the last virtual point otherwise stayed the
         // click point in Live mode; not proven to be EA's own exit step.
         try { this.A11yBuildLog("resync native return=" + String(CommunicationManager.CallGameService("SetVirtualCursorPosition",{"x":-1,"y":-1},true))); }
         catch(resyncError:Error) { this.A11yBuildLog("resync error=" + resyncError.name + ":" + resyncError.message); }
         // EA's CenterInputAdapterBase restores UI mouse routing separately
         // from disabling its virtual cursor. Otherwise clicks can reach the
         // world beneath a modal even after the cursor itself is disabled.
         try { this.A11yBuildLog("mouse restore return=" + String(CommunicationManager.CallGameService("SetMouseInputEnabled",true))); }
         catch(mouseError:Error) { this.A11yBuildLog("mouse restore error=" + mouseError.name + ":" + mouseError.message); }
         this.A11yBuildSnapshot("disable-after");
      }

      public function A11yBuildSetControls(enabled:Boolean) : void
      {
         this.mA11yBuildControls = enabled;
         if(enabled) { return; }
         // Release only state this feature owned. An off heartbeat must not
         // reset the game's cursor when the feature was never used.
         var owned:Boolean = this.mA11yBuildCursor || this.mA11yBuildPositionKnown || this.mA11yBuildMarker != null;
         this.A11yBuildDisable(owned);
         this.mA11yBuildPositionKnown = false;
         this.A11yBuildProductForget();
         this.mA11yBuildProductModals = 0;
         if(owned) { this.A11yBuildReply(0,"off"); }
      }

      public function A11yBuildFrame() : void
      {
         if(!this.mA11yBuildControls)
         {
            if(this.mA11yBuildCursor || this.mA11yBuildPositionKnown || this.mA11yBuildMarker != null || this.mA11yBuildProduct != null || this.mA11yBuildProductModals != 0) { this.A11yBuildSetControls(false); }
            return;
         }
         try
         {
         if(this.mA11yKeyboard && this.A11yWorldHudMode() == 2) { this.A11yBuildProductObserve(); }
         this.A11yBuildProductFrame();
         this.A11yBuildProjectionFrame();
         if(!this.mA11yKeyboard || getTimer() > this.mA11yKeyboardLease || this.A11yWorldHudMode() != 2)
         {
            this.mA11yBuildPositionKnown = false; this.A11yBuildProductForget();
         }
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
         var fromMenu:Boolean = false;
         try
         {
            if(action.indexOf("menu:") == 0)
            {
               action = action.substr(5);
               if(["left","right","up","down","click","cancel","rotateleft","rotateright","status","fine","coarse","center"].indexOf(action) < 0) { this.A11yBuildReply(serial,"unavailable"); return; }
               fromMenu = true;
            }
            // Explicit cleanup also reaches a fresh Live UI after Build teardown.
            // Unlike an off setting heartbeat, Python sends this to release use.
            if(action == "off") { this.A11yBuildDisable(true); this.mA11yBuildPositionKnown = false; this.A11yBuildProductForget(); this.A11yBuildReply(serial,"off"); return; }
            if(!this.mA11yBuildControls) { this.A11yBuildReply(serial,"unavailable"); return; }
            if(this.mA11yBuildMarker != null) { this.A11yBuildUnbind(); }
            if(this.A11yWorldHudMode() != 2 || !this.mA11yKeyboard || getTimer() > this.mA11yKeyboardLease) { this.mA11yBuildPositionKnown = false; this.A11yBuildProductForget(); this.A11yBuildDisable(); this.A11yBuildReply(serial,"unavailable"); return; }
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
            // Opening a menu disables the native cursor, but an explicit
            // menu choice may resume its position after that menu closes.
            // This never bypasses the modal, editing, mode or lease guards.
            if(action == "on" || (fromMenu && !this.mA11yBuildCursor))
            {
               if(action == "on" || !this.mA11yBuildPositionKnown)
               {
                  input = getDefinitionByName("olympus.utils.InputUtils");
                  this.mA11yBuildX = int(input["sMouseX"]);
                  this.mA11yBuildY = int(input["sMouseY"]);
               }
               this.A11yBuildEnable(bounds);
               if(this.mA11yBuildCursor && fromMenu)
               {
                  this.mA11yBuildX = int(Math.max(bounds.left,Math.min(bounds.right,this.mA11yBuildX)));
                  this.mA11yBuildY = int(Math.max(bounds.top,Math.min(bounds.bottom,this.mA11yBuildY)));
                  CommunicationManager.CallGameService("SetVirtualCursorPosition",{"x":this.mA11yBuildX,"y":this.mA11yBuildY},true);
               }
            }
            if(!this.mA11yBuildCursor) { this.A11yBuildReply(serial,"unavailable"); return; }
            if((fromMenu || action == "on") && action != "cancel") { this.A11yBuildProductRestore(); }
            if(action == "cancel")
            {
               this.A11yBuildProductForget();
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
            if(action == "status" || action == "on") { this.A11yBuildSnapshot("command-" + action); }
            this.A11yBuildReply(serial,action);
         }
         catch(e:Error)
         {
            this.A11yBuildDisable();
            this.A11yBuildReply(serial,"unavailable");
         }
      }

      // END A11Y V10 NATIVE BUILD CURSOR

      // BEGIN A11Y V11 STARTUP SOCKET (outbound only)
      // Speech transport for the main menu and Create a Sim before a save
      // loads, when PostServerCommand has no simulation to reach. Flash writes
      // narration lines to a loopback listener owned by our Python; Python
      // never writes back, so no socket data event is ever delivered into the
      // VM (the V10 request/response protocol coincided with five native
      // crashes at boot, at the menu and in CAS). Keyboard mode is signalled
      // by the port Python listens on: 45993 simplified keyboard,
      // 45994 speech only, 45995 original keyboard navigation.
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
      protected var mA11yInterstitialAt:int = 0;
      // Diagnostic builds flip this (build script source_transform): post the
      // inspect dump after every startup-mode Tab, since a11y.inspect_ui cannot
      // reach Flash before a client exists. Never true in a shipped build.
      protected var mA11yDiagInspectOnTab:Boolean = false;

      public function A11yStartupInstall() : void
      {
         try
         {
            if(this.mA11yStartupInstalled || this.mTooltipsLayer == null) { return; }
            this.mA11yStartupInstalled = true;
            // Same listener host as A11yModalFrame: a stage listener stopped
            // firing after a save loaded (2026-09-16 run 5), which left the
            // mode frozen at startup and the poller silenced in the lot.
            this.mTooltipsLayer.addEventListener(Event.ENTER_FRAME,this.A11yStartupFrame,false,0,true);
         }
         catch(e:Error) { }
      }

      // True while no simulation client exists: from boot until the first
      // A11yHook (sent by Python at every zone load), and again whenever the
      // main menu dock is visible.
      // EA's UIManager (an ancestor of the tooltips layer, the same node the
      // layout-manager walk finds) keeps the authoritative game state in its
      // public mGameState, updated on every GameStateChanged. Reading it costs
      // one property lookup per frame; no CallGameService round trip.
      // Number, not uint: FFDec's recompile of int/uint coercions is the one
      // known miscompile in this pipeline, and the state ids fit a Number exactly.
      protected var mA11yUIManager:Object = null;
      protected var mA11yGameStateSeen:Number = 0;

      public function A11yGameState() : Number
      {
         var node:DisplayObject = null;
         try
         {
            if(this.mA11yUIManager == null)
            {
               node = this.mTooltipsLayer;
               while(node != null)
               {
                  if("mGameState" in node && "layoutMgr" in node) { this.mA11yUIManager = node; break; }
                  node = node.parent;
               }
            }
            if(this.mA11yUIManager != null) { return Number(this.mA11yUIManager["mGameState"]); }
         }
         catch(e:Error) { this.mA11yUIManager = null; }
         return 0;
      }

      public function A11yStartupZoneless() : Boolean
      {
         var state:Number = 0;
         try
         {
            // Authoritative first (2026-09-24). Observed: after returning from
            // a lot to the main menu, startup mode never re-armed (no
            // startup-v11-active mark). Hypothesis: the HUD widgets stay live
            // under the launcher, so the heuristic below never judged the menu
            // zoneless. EA's game state settles it either way.
            state = this.A11yGameState();
            if(state != this.mA11yGameStateSeen)
            {
               this.mA11yGameStateSeen = state;
               this.A11yPostToPython("a11y.mark","gamestate-" + state);
            }
            // GameStates.MAIN_MENU / ENTER_MAIN_MENU: no simulation client.
            if(state == 1273744144 || state == 3712041429) { this.mA11yZoneSeen = false; return true; }
            // GameStates.PLAY / BUILD: a loaded client owns the keys.
            if(state == 270579719 || state == 2919482169) { this.mA11yZoneSeen = true; return false; }
            // GameStates.CAS: from the menu there is no client (startup mode);
            // entered from a lot the client persists (native mode).
            if(state == 983016380) { return !this.mA11yZoneSeen; }
            if(this.A11yWorldHudMode() != 0) { this.mA11yZoneSeen = true; return false; }
            if(this.A11yIsLive(this.A11yLoadedWidget("GameEntryDock"))) { this.mA11yZoneSeen = false; return true; }
            return !this.mA11yZoneSeen;
         }
         catch(e:Error) { }
         return false;
      }

      // Main menu: the five navigation buttons (Resume, Load, New Game,
      // Gallery, Play Scenario) are the whole Tab ring (user decision
      // 2026-09-16); promos, marketplace tabs and the wallet stay out.
      public function A11yLauncherNavigation() : DisplayObject
      {
         var launcher:Object = null;
         var nav:DisplayObject = null;
         try
         {
            launcher = this.A11yLoadedWidget("GameEntryLauncher");
            if(launcher != null && "mcNavigation" in launcher)
            {
               nav = launcher["mcNavigation"] as DisplayObject;
               if(this.A11yIsLive(nav)) { return nav; }
            }
         }
         catch(e:Error) { }
         return null;
      }

      // New-game season selection is one choice, not the surrounding map toolbar.
      public function A11ySeasonScope() : DisplayObject
      {
         var world:Object = this.A11yLoadedWidget("GameEntryWorldSelection");
         if(world == null || !("mcSeasonSelection" in world)) { return null; }
         var scope:DisplayObject = world["mcSeasonSelection"] as DisplayObject;
         if(!this.A11yIsLive(scope) || !("btnSpring" in scope) || !("btnConfirm" in scope)) { return null; }
         if(!this.A11yIsLive(Object(scope)["btnSpring"]) || !Object(scope)["btnConfirm"]["mouseEnabled"]) { return null; }
         return scope;
      }

      public function A11ySeasonButton(item:DisplayObject) : Boolean
      {
         if(item == null || item.parent == null) { return false; }
         return getQualifiedClassName(item.parent) == "widgets.GameEntry.WorldSelection.SeasonSelect::SeasonSelectContainer" && ["btnSpring","btnSummer","btnFall","btnWinter"].indexOf(item.name) >= 0;
      }

      public function A11ySeasonActivate(item:DisplayObject, confirm:Boolean) : Boolean
      {
         if(!this.A11ySeasonButton(item)) { return false; }
         if(item.parent != this.A11ySeasonScope() || !this.A11yIsLive(item)) { return true; }
         var scope:Object = item.parent;
         if(this.A11yClickControl(item))
         {
            // Native selection enables Confirm synchronously. Use its own
            // handler so EA sets the season and completes the normal transition.
            if(confirm) { this.A11yClickControl(scope["btnConfirm"] as DisplayObject); }
            else { this.A11yAnnounceDisplay(item,"a11y.focus_enc",true); }
         }
         return true;
      }

      public function A11ySeasonBounds(item:DisplayObject) : Rectangle
      {
         var bounds:Rectangle = this.A11ySortBounds(item);
         if(this.A11ySeasonButton(item) && "txtName" in item)
         {
            var label:DisplayObject = Object(item)["txtName"] as DisplayObject;
            if(this.A11yIsLive(label))
            {
               // Hidden description artwork enlarges getBounds below the card.
               // The native visible name is the bottom of the selectable card.
               var bottom:Number = label.getBounds(item.stage).bottom + 8;
               // The name field includes blank padding. Keep the border above
               // the description rather than drawing through its first line.
               if("mcDescription" in item && Object(item)["mcDescription"] != null)
               {
                  var holder:Object = Object(item)["mcDescription"];
                  if("txtDescription" in holder)
                  {
                     var description:DisplayObject = holder["txtDescription"] as DisplayObject;
                     if(this.A11yIsLive(description))
                     {
                        var descriptionTop:Number = description.getBounds(item.stage).top - 4;
                        if(descriptionTop > label.getBounds(item.stage).top)
                        {
                           bottom = Math.min(bottom,descriptionTop);
                        }
                     }
                  }
               }
               if(bottom > bounds.top && bottom < bounds.bottom) { bounds.bottom = bottom; }
            }
         }
         return bounds;
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
            var allowed:Array = ["a11y.speak_enc","a11y.widget_enc","a11y.focus_enc","a11y.widgetname_enc","a11y.dialog_enc","a11y.scope_enc","a11y.event_enc","a11y.context_enc","a11y.inspect_enc","a11y.modalstate","a11y.blocking","a11y.clock_enc","a11y.mood_enc","a11y.inputfence","a11y.stop","a11y.mark"];
            if(this.mA11yStartupActive && allowed.indexOf(command) >= 0)
            {
               var now:int = getTimer();
               if(now - this.mA11yStartupPostWindow >= 1000)
               {
                  this.mA11yStartupPostWindow = now;
                  this.mA11yStartupPostCount = 0;
               }
               // State messages cannot be lost behind noisy hovers.
               if(this.mA11yStartupPostCount >= 40 && command != "a11y.inputfence" && command != "a11y.modalstate" && command != "a11y.blocking" && command != "a11y.mark") { return true; }
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
            this.mA11yModalReported = ""; this.mA11yBlockingReported = "";
            this.mA11yOwnerReported = "";
            this.A11yStartupWrite("HELLO|A11Y_STARTUP_V2|" + this.mA11yStartupPort);
            if(this.mA11yStartupPort == 45993 || this.mA11yStartupPort == 45995)
            {
               this.A11ySetSimplifiedMenus(this.mA11yStartupPort == 45993);
               this.A11yKeyboardOn();
            }
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
            if(!wasConnected) { this.mA11yStartupPort = this.A11yNextStartupPort(this.mA11yStartupPort); }
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
               if(key == 9) { this.A11yTabControl(modifier == 1 ? -1 : 1); if(this.mA11yDiagInspectOnTab) { this.A11yInspect(); } }
               else if(key == 13) { this.A11yActivate(); }
               else if(key == 32) { this.A11yActivate(false); }
               else if(key == 8) { this.A11yReturnRow(); }
               else if(key == 27) { this.A11yDismiss(); }
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
                     this.mA11yStartupPort = this.A11yNextStartupPort(this.mA11yStartupPort);
                  }
                  return;
               }
               if(!this.mA11yStartupSocket["connected"]) { this.A11yStartupClose(5000); return; }
               active = this.A11yStartupZoneless();
               if(active != this.mA11yStartupActive)
               {
                  if(!active) { this.A11yPostToPython("a11y.mark","startup-v11-native"); }
                  this.mA11yStartupActive = active;
                  this.mA11yStartupKeys.length = 0;
                  this.mA11yModalReported = ""; this.mA11yBlockingReported = "";
                  this.mA11yOwnerReported = "";
                  if(active) { this.A11yPostToPython("a11y.mark","startup-v11-active"); }
               }
               if(active && this.mA11yKeyboard)
               {
                  this.mA11yKeyboardLease = now + 2000;
                  if(this.mA11yInterstitialAt > 0 && now >= this.mA11yInterstitialAt)
                  {
                     this.mA11yInterstitialAt = 0;
                     if(this.A11yIsLive(this.mA11yActiveModalRoot) && getQualifiedClassName(this.mA11yActiveModalRoot).indexOf("FSInterstitialMessageDialog") >= 0) { this.A11yDismiss(); }
                  }
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

      // BEGIN A11Y GUIDED NEW GAME
      // A new family's Create a Sim is walked step by step in EA's own
      // dialogs (DialogManager + DialogContainer, as CASNameField's
      // CustomPronounsDialog does), and each choice is applied through the
      // CAS game service EA's own panels call. No CAS movie is rebuilt; the
      // look editors stay EA's. See docs/development/changes/guided-new-game*.md.
      public function A11yGuideFrame() : void
      {
         var now:int = getTimer();
         var nameField:Object = null;
         var nameButton:DisplayObject = null;
         try
         {
            if(now < this.mA11yGuideCheckAt) { return; }
            this.mA11yGuideCheckAt = now + 250;
            // Past Create a Sim: the season, world, lot and move-in steps.
            if(this.mA11yGuidePhase != "") { this.A11yGuideHomeFrame(now); return; }
            nameField = this.A11yLoadedWidget("CASNameField");
            if(!this.A11yIsLive(nameField as DisplayObject))
            {
               // CAS closed: the next CAS session is offered the guide again.
               this.mA11yGuideState = "";
               this.mA11yGuideTraitsOpen = false;
               this.mA11yGuideNames = new Object();
               this.mA11yGuideNewSim = false;
               this.mA11yGuideReadyAt = 0;
               return;
            }
            if(this.mA11yGuideState == "editing")
            {
               // CAS's own name editor is open (CASNameFieldMain hides its
               // name button while editing). Enter saves, Escape reverts;
               // either way the guide continues when the editor closes.
               nameButton = nameField["btnTextEffect"] as DisplayObject;
               if(nameButton != null && !nameButton.visible) { this.mA11yGuideEditSeen = true; }
               else if(this.mA11yGuideEditSeen) { this.mA11yGuideState = "open"; this.A11yGuideNameResult(); }
               else if(now - this.mA11yGuideEditAt > 3000) { this.mA11yGuideState = "open"; this.A11yGuideNoEditor(); }
               return;
            }
            if(this.mA11yGuideState == "adding")
            {
               // CasAddSim switches CAS to the new Sim; wait until it is current.
               if(String(this.A11yGuideSimInfo()["simId"]) != this.mA11yGuideAddFrom || now - this.mA11yGuideEditAt > 5000)
               {
                  this.mA11yGuideState = "open";
                  this.A11yGuideNameDialog();
               }
               return;
            }
            if(this.mA11yGuideState != "") { return; }
            this.mA11yGuideCheckAt = now + 500;
            if(this.A11yCASStoryScope() != null || CommunicationManager.CallGameService("GetInCasStoryMode") == true)
            {
               // The questionnaire prompt or the questionnaire itself.
               this.mA11yGuideReadyAt = 0;
               return;
            }
            if(this.mA11yManagedDialog != null) { this.mA11yGuideReadyAt = 0; return; }
            if(CommunicationManager.CallGameService("CasIsNewFamily") != true)
            {
               this.mA11yGuideState = "skip";
               this.A11yPostToPython("a11y.mark","guide-skip-not-new-family");
               return;
            }
            // Let CAS settle for a second after the questionnaire choice.
            if(this.mA11yGuideReadyAt == 0) { this.mA11yGuideReadyAt = now; return; }
            if(now - this.mA11yGuideReadyAt < 1000) { return; }
            this.A11yPostToPython("a11y.mark","guide-offered");
            this.A11yGuideIntro();
         }
         catch(e:Error) { this.A11yGuideFailed(e); }
      }

      // One guide dialog: title, prompt and buttons, all in EA's own dialog.
      // Every button and Cancel call A11yGuideAnswer with the step and the
      // button's index (-1 for Cancel). Only buttons: typing happens in
      // CAS's own name editor, which TS4 Access already reads and drives.
      public function A11yGuideDialog(step:String, title:String, prompt:String, buttons:Array) : void
      {
         var requestClass:Class = getDefinitionByName("widgets.Dialog.data.LocalRequestData") as Class;
         var actionClass:Class = getDefinitionByName("widgets.Dialog.actions.CallbackDialogAction") as Class;
         var containerClass:Class = getDefinitionByName("widgets.Dialog.dialogs.DialogContainer") as Class;
         var headerClass:Class = getDefinitionByName("widgets.Dialog.headers.TitleBodyHeader") as Class;
         var footerClass:Class = getDefinitionByName("widgets.Dialog.footers.DialogButtonFooter") as Class;
         var wrapperClass:Class = getDefinitionByName("olympus.dialog.DialogRequest") as Class;
         var managerClass:Object = getDefinitionByName("olympus.dialog.DialogManager");
         var data:Object = new requestClass();
         var container:Object = new containerClass();
         var index:int = 0;
         var serial:int = 0;
         this.mA11yGuideSerial = this.mA11yGuideSerial + 1;
         serial = this.mA11yGuideSerial;
         data["title"] = title;
         data["promptText"] = prompt;
         data["dialog_id"] = "A11yGuide" + serial;
         while(index < buttons.length)
         {
            data["actions"].push(new actionClass(this.A11yGuideAnswer,{"step":step,"index":index,"serial":serial},String(buttons[index])));
            index = index + 1;
         }
         data["cancellationAction"] = new actionClass(this.A11yGuideAnswer,{"step":step,"index":-1,"serial":serial},null);
         container["Header"] = new headerClass();
         container["Footer"] = new footerClass();
         this.mA11yGuideDialogId = String(data["dialog_id"]);
         this.mA11yGuideState = "open";
         managerClass["RequestDialog"](new wrapperClass(container,data));
      }

      public function A11yGuideAnswer(answer:Object) : void
      {
         var step:String = "";
         var index:int = -1;
         var picked:Object = null;
         try
         {
            if(answer == null || int(answer["serial"]) != this.mA11yGuideSerial) { return; }
            step = String(answer["step"]);
            index = int(answer["index"]);
            // List steps keep their choices in mA11yGuideList; the last
            // button (and Cancel) is always Back.
            if(index >= 0 && index < this.mA11yGuideList.length) { picked = this.mA11yGuideList[index]; }
            if(step == "intro")
            {
               if(index == 0) { this.A11yGuideNameDialog(); }
               else { this.A11yGuideFinish(); }
            }
            else if(step == "name")
            {
               if(index == 0) { this.A11yGuideTypeName(); }
               else if(index == 1) { this.A11yGuideRandomName(); }
               else if(index == 2) { this.A11yGuideNameResult(); }
               else { this.A11yGuideIntro(); }
            }
            else if(step == "named")
            {
               if(index == 0) { this.A11yGuideAgeDialog(); }
               else { this.A11yGuideNameDialog(); }
            }
            else if(step == "noeditor") { this.A11yGuideNameDialog(); }
            else if(step == "age")
            {
               if(picked != null) { this.A11yGuideSetAge(int(picked)); this.A11yGuideGenderDialog(); }
               else { this.A11yGuideNameResult(); }
            }
            else if(step == "gender")
            {
               if(picked != null) { this.A11yGuideSetGender(int(picked)); this.A11yGuideTraitsDialog(); }
               else { this.A11yGuideAgeDialog(); }
            }
            else if(step == "traits")
            {
               if(picked == "add") { this.A11yGuideTraitGroupsDialog(); }
               else if(picked == "remove") { this.A11yGuideTraitRemoveDialog(); }
               else if(picked == "next") { this.A11yGuideTraitsClose(); this.A11yGuideAspirationCategories(); }
               else { this.A11yGuideTraitsClose(); this.A11yGuideGenderDialog(); }
            }
            else if(step == "traitgroup")
            {
               if(picked != null) { this.A11yGuideTraitListDialog(picked); }
               else { this.A11yGuideTraitsDialog(); }
            }
            else if(step == "traitpick")
            {
               if(picked != null)
               {
                  CommunicationManager.CallGameService("AddTraitToSim",{"traitID":String(picked)});
                  this.A11yPostToPython("a11y.mark","guide-trait-add-" + String(picked) + "-now-" + this.A11yGuideEquippedIds().length);
                  this.A11yGuideTraitsDialog();
               }
               else { this.A11yGuideTraitGroupsDialog(); }
            }
            else if(step == "traitremove")
            {
               if(picked != null)
               {
                  CommunicationManager.CallGameService("RemoveTraitFromSim",{"traitID":String(picked)});
                  this.A11yPostToPython("a11y.mark","guide-trait-remove-" + String(picked) + "-now-" + this.A11yGuideEquippedIds().length);
               }
               this.A11yGuideTraitsDialog();
            }
            else if(step == "aspcat")
            {
               if(picked != null) { this.A11yGuideAspirationTracks(picked); }
               else { this.A11yGuideTraitsDialog(); }
            }
            else if(step == "asptrack")
            {
               if(picked != null)
               {
                  CommunicationManager.CallGameService("SetSimAspiration",{"uid":String(picked["uid"])});
                  this.mA11yGuideAspiration = String(picked["label"]);
                  this.A11yGuideSummary();
               }
               else { this.A11yGuideAspirationCategories(); }
            }
            else if(step == "summary")
            {
               if(picked == "done" && this.mA11yGuideNewSim && this.A11yGuideRelations().length > 0) { this.mA11yGuideNewSim = false; this.A11yGuideRemember(); this.A11yGuideRelationsDialog(); }
               else if(picked == "done") { this.A11yGuideReady(); }
               else if(picked == "name") { this.A11yGuideNameDialog(); }
               else if(picked == "age") { this.A11yGuideAgeDialog(); }
               else if(picked == "traits") { this.A11yGuideTraitsDialog(); }
               else if(picked == "aspiration") { this.A11yGuideAspirationCategories(); }
               else if(picked == "extras") { this.A11yGuideExtrasDialog(); }
               else { this.A11yGuideAspirationCategories(); }
            }
            else if(step == "extras")
            {
               if(picked == "voice") { this.A11yGuideVoiceDialog(); }
               else if(picked == "pitch") { this.A11yGuidePitchDialog(); }
               else if(picked == "walk") { this.A11yGuideWalkDialog(); }
               else { this.A11yGuideSummary(); }
            }
            else if(step == "voice")
            {
               if(picked != null) { CommunicationManager.CallGameService("SetSimVoiceActor",int(picked)); this.A11yGuideVoiceDialog(); }
               else { this.A11yGuideExtrasDialog(); }
            }
            else if(step == "pitch")
            {
               if(picked != null) { CommunicationManager.CallGameService("SetSimVoicePitch",{"value":Number(picked),"slider_mouse_up":true}); this.A11yGuidePitchDialog(); }
               else { this.A11yGuideExtrasDialog(); }
            }
            else if(step == "walk")
            {
               if(picked != null) { CommunicationManager.CallGameService("CasSetWalkCycleTrait",{"traitID":String(picked)}); this.A11yGuideWalkDialog(); }
               else { this.A11yGuideExtrasDialog(); }
            }
            else if(["ready","relations","relpick","switch","adult","badname","homeerror","household","season","world","lots","furnish","toodear","cantbuy","nopanel","play"].indexOf(step) >= 0)
            {
               this.A11yGuideHomeAnswer(step,index,picked);
            }
         }
         catch(e:Error) { this.A11yGuideFailed(e); }
      }

      // A list step: one button per choice, then Back. Choices are kept in
      // mA11yGuideList in button order.
      public function A11yGuideList(step:String, title:String, prompt:String, labels:Array, values:Array) : void
      {
         var buttons:Array = labels.slice();
         buttons.push("Back");
         this.mA11yGuideList = values;
         this.A11yGuideDialog(step,title,prompt,buttons);
      }

      // Text of a game string, given raw service data or a LocKey.
      public function A11yGuideText(raw:Object) : String
      {
         var locClass:Class = null;
         var key:Object = null;
         try
         {
            if(raw == null) { return ""; }
            if(typeof(raw) == "string") { return String(raw); }
            locClass = getDefinitionByName("olympus.localization.LocKey") as Class;
            key = raw is locClass ? raw : new locClass(raw);
            return String(key.toString({"simId":"0"}));
         }
         catch(e:Error) { }
         return "";
      }

      public function A11yGuideSay(text:String) : void
      {
         this.A11yPostToPython("a11y.speak_enc",encodeURIComponent("0|0|" + text));
      }

      public function A11yGuideIntro() : void
      {
         this.mA11yGuideList = new Array();
         this.A11yGuideDialog("intro","Create your Sim",
            "Welcome! This guide makes your Sim one step at a time: name, age and gender, traits, then aspiration. Each step is a short window: choose an option to continue. You can change how your Sim looks at the end, or keep the look the game made.",
            ["Start","Skip the guide and use the full Create a Sim screen"]);
      }

      public function A11yGuideSimInfo() : Object
      {
         var info:Object = null;
         try { info = CommunicationManager.CallGameService("CASGetSimInfo"); }
         catch(e:Error) { info = null; }
         return info != null ? info : new Object();
      }

      public function A11yGuideSimName() : String
      {
         var info:Object = this.A11yGuideSimInfo();
         var first:String = info["firstName"] != undefined && info["firstName"] != null ? String(info["firstName"]) : "";
         var last:String = info["lastName"] != undefined && info["lastName"] != null ? String(info["lastName"]) : "";
         return (first + " " + last).replace(/^\s+|\s+$/g,"");
      }

      public function A11yGuideNameDialog() : void
      {
         var name:String = this.A11yGuideSimName();
         this.mA11yGuideList = new Array();
         this.A11yGuideDialog("name","Step 1: Name",
            (name != "" ? "Your Sim is called " + name + " right now. " : "") +
            "Choose Type the name to type your own: the name boxes open on the first name. Type it, press Tab, type the last name, then press Enter. Or choose Random name and the game picks one.",
            ["Type the name","Random name","Keep this name","Back"]);
      }

      public function A11yGuideTypeName() : void
      {
         // CASNameFieldMain.OnCASNameFieldSetEditMode opens its own editor.
         this.mA11yGuideState = "editing";
         this.mA11yGuideEditSeen = false;
         this.mA11yGuideEditAt = getTimer();
         CommunicationManager.SendUIMessage("CASNameFieldSetEditMode",{"bEditMode":true});
         this.A11yGuideSay("Name boxes open. Type the first name, press Tab, type the last name, then press Enter. Escape cancels.");
      }

      public function A11yGuideRandomName() : void
      {
         // The same as CAS's dice buttons: CASNameFieldMain.HandleRandomizeSimName
         // randomizes both names and writes them through CASSetSimName.
         CommunicationManager.SendUIMessage("CASRandomizeSimName",{"overrideCurrent":true});
         this.A11yGuideNameResult();
      }

      public function A11yGuideNameResult() : void
      {
         var name:String = this.A11yGuideSimName();
         this.mA11yGuideList = new Array();
         this.A11yGuideDialog("named","Name: " + (name != "" ? name : "not set"),
            name != "" ? "Your Sim is called " + name + ". Choose Next for age and gender, or Change the name." : "Your Sim has no name yet.",
            ["Next","Change the name"]);
      }

      public function A11yGuideNoEditor() : void
      {
         this.mA11yGuideList = new Array();
         this.A11yGuideDialog("noeditor","Name boxes did not open",
            "The name boxes did not open. Choose OK to go back to the name step, then try Random name or Type the name again.",
            ["OK"]);
      }

      // Step 2: age. GetAgesData is what CAS's AgeGenderPanel lists; babies
      // are left out there too. SetSimAge is followed by the same
      // RefreshSimAgeGender message the panel sends.
      public function A11yGuideAgeDialog() : void
      {
         var info:Object = this.A11yGuideSimInfo();
         var species:int = info["speciesType"] != undefined ? int(info["speciesType"]) : 1;
         var current:int = int(CommunicationManager.CallGameService("GetSimAge"));
         var ages:Array = CommunicationManager.CallGameService("GetAgesData",{"species":species,"age":0}) as Array;
         var order:Array = [128,2,4,8,16,32,64];
         var labels:Array = new Array();
         var values:Array = new Array();
         var i:int = 0;
         var j:int = 0;
         var label:String = "";
         while(i < order.length)
         {
            j = 0;
            while(ages != null && j < ages.length)
            {
               if(int(ages[j]["ageType"]) == int(order[i]))
               {
                  label = this.A11yGuideText(ages[j]["name"]);
                  if(label == "") { label = "Age " + order[i]; }
                  labels.push(int(order[i]) == current ? label + " (now)" : label);
                  values.push(int(order[i]));
               }
               j = j + 1;
            }
            i = i + 1;
         }
         this.A11yGuideList("age","Step 2: Age",
            "Choose your Sim's age. Young Adult is the usual choice for a first Sim: they can work, date and start a family.",labels,values);
      }

      public function A11yGuideSetAge(age:int) : void
      {
         if(int(CommunicationManager.CallGameService("GetSimAge")) != age) { CommunicationManager.CallGameService("SetSimAge",age); }
         this.A11yGuideRefreshAgeGender();
      }

      public function A11yGuideRefreshAgeGender() : void
      {
         CommunicationManager.SendUIMessage("RefreshSimAgeGender",{
            "simAge":int(CommunicationManager.CallGameService("GetSimAge")),
            "simGender":int(CommunicationManager.CallGameService("GetSimGender")),
            "simSpecies":uint(CommunicationManager.CallGameService("GetSimSpecies"))});
      }

      // Step 3: gender. CAS's panel calls SetSimGender with no argument to
      // switch to the other gender.
      public function A11yGuideGenderDialog() : void
      {
         var info:Object = this.A11yGuideSimInfo();
         var species:int = info["speciesType"] != undefined ? int(info["speciesType"]) : 1;
         var age:int = int(CommunicationManager.CallGameService("GetSimAge"));
         var current:int = int(CommunicationManager.CallGameService("GetSimGender"));
         var genders:Object = getDefinitionByName("gamedata.shared.SimGenderTypes");
         var values:Array = [int(genders["FEMALE"]),int(genders["MALE"])];
         var labels:Array = new Array();
         var i:int = 0;
         var label:String = "";
         while(i < values.length)
         {
            label = this.A11yGuideText(genders["GetGenderStringKey"](values[i],species,age));
            if(label == "") { label = i == 0 ? "Female" : "Male"; }
            labels.push(int(values[i]) == current ? label + " (now)" : label);
            i = i + 1;
         }
         this.A11yGuideList("gender","Step 3: Gender","Choose your Sim's gender.",labels,values);
      }

      public function A11yGuideSetGender(gender:int) : void
      {
         if(int(CommunicationManager.CallGameService("GetSimGender")) != gender)
         {
            CommunicationManager.CallGameService("SetSimGender");
            this.A11yGuideRefreshAgeGender();
         }
      }

      // Traits: the same groups and per-group lists CAS's trait selector
      // shows (GetTraitGroups, GetAllSimTraitsInfo). Returns
      // [{id, title, traits:[{id, title, equipped, conflicts}]}].
      public function A11yGuideTraitScan() : Array
      {
         var info:Object = this.A11yGuideSimInfo();
         var simId:String = info["simId"] != undefined ? String(info["simId"]) : "0";
         var groups:Array = CommunicationManager.CallGameService("GetTraitGroups") as Array;
         var out:Array = new Array();
         var raw:Array = null;
         var traits:Array = null;
         var i:int = 0;
         var j:int = 0;
         while(groups != null && i < groups.length)
         {
            raw = CommunicationManager.CallGameService("GetAllSimTraitsInfo",{"simId":simId,"groupId":groups[i]["groupId"]}) as Array;
            traits = new Array();
            j = 0;
            while(raw != null && j < raw.length)
            {
               // CAS's trait panel keeps personality traits only
               // (SimTraitsInfo.TRAIT_PERSONALITY is "0").
               if(raw[j]["type"] != undefined && raw[j]["type"] != null && String(raw[j]["type"]) != "0") { j = j + 1; continue; }
               traits.push({"id":String(raw[j]["id"]),"title":this.A11yGuideText(raw[j]["title"]),"equipped":raw[j]["equipped"] == true,
                  "conflicts":raw[j]["conflictingTraitIds"] != null ? raw[j]["conflictingTraitIds"] : new Array()});
               j = j + 1;
            }
            if(traits.length > 0) { out.push({"id":groups[i]["groupId"],"title":this.A11yGuideText(groups[i]["title"]),"traits":traits}); }
            i = i + 1;
         }
         return out;
      }

      public function A11yGuideEquippedIds() : Array
      {
         var raw:Array = CommunicationManager.CallGameService("CasGetEquippedTraits") as Array;
         var out:Array = new Array();
         var i:int = 0;
         while(raw != null && i < raw.length) { out.push(String(raw[i])); i = i + 1; }
         return out;
      }

      public function A11yGuideEquipped(scan:Array) : Array
      {
         var out:Array = new Array();
         var ids:Array = this.A11yGuideEquippedIds();
         var i:int = 0;
         var j:int = 0;
         while(i < scan.length)
         {
            j = 0;
            while(j < scan[i]["traits"].length)
            {
               if(ids.indexOf(String(scan[i]["traits"][j]["id"])) >= 0) { scan[i]["traits"][j]["equipped"] = true; }
               if(scan[i]["traits"][j]["equipped"]) { out.push(scan[i]["traits"][j]); }
               j = j + 1;
            }
            i = i + 1;
         }
         return out;
      }

      // EquippedTraitsAsp brackets trait edits with CasPersonalityTraitsUIOpened
      // and CasPersonalityTraitsUIDone; the guide does the same.
      public function A11yGuideTraitsOpen() : void
      {
         if(this.mA11yGuideTraitsOpen) { return; }
         this.mA11yGuideTraitsOpen = true;
         CommunicationManager.CallGameService("CasPersonalityTraitsUIOpened");
      }

      public function A11yGuideTraitsClose() : void
      {
         if(!this.mA11yGuideTraitsOpen) { return; }
         this.mA11yGuideTraitsOpen = false;
         CommunicationManager.CallGameService("CasPersonalityTraitsUIDone");
         this.A11yPostToPython("a11y.mark","guide-traits-done-" + this.A11yGuideEquippedIds().length);
      }

      public function A11yGuideTraitsDialog() : void
      {
         this.A11yGuideTraitsOpen();
         var info:Object = this.A11yGuideSimInfo();
         var max:int = info["maxTraits"] != undefined ? int(info["maxTraits"]) : 3;
         var equipped:Array = this.A11yGuideEquipped(this.A11yGuideTraitScan());
         var names:Array = new Array();
         var labels:Array = new Array();
         var values:Array = new Array();
         var i:int = 0;
         while(i < equipped.length) { names.push(equipped[i]["title"]); i = i + 1; }
         if(equipped.length < max) { labels.push("Add a trait"); values.push("add"); }
         if(equipped.length > 0) { labels.push("Remove a trait"); values.push("remove"); }
         labels.push("Next: aspiration");
         values.push("next");
         this.A11yGuideList("traits","Step 4: Traits",
            "Traits shape your Sim's personality. Your Sim can have " + max + ". " +
            (equipped.length > 0 ? "Chosen: " + names.join(", ") + "." : "None chosen yet."),labels,values);
      }

      public function A11yGuideTraitGroupsDialog() : void
      {
         var scan:Array = this.A11yGuideTraitScan();
         var labels:Array = new Array();
         var values:Array = new Array();
         var i:int = 0;
         while(i < scan.length) { labels.push(scan[i]["title"]); values.push(scan[i]); i = i + 1; }
         this.A11yGuideList("traitgroup","Add a trait","Choose a kind of trait.",labels,values);
      }

      public function A11yGuideTraitListDialog(group:Object) : void
      {
         var scan:Array = this.A11yGuideTraitScan();
         var taken:Array = this.A11yGuideEquipped(scan);
         var traits:Array = null;
         var labels:Array = new Array();
         var values:Array = new Array();
         var i:int = 0;
         var j:int = 0;
         var clash:Boolean = false;
         while(i < scan.length)
         {
            if(String(scan[i]["id"]) == String(group["id"])) { traits = scan[i]["traits"]; }
            i = i + 1;
         }
         i = 0;
         while(traits != null && i < traits.length)
         {
            // Leave out traits already chosen and traits that clash with them,
            // as CAS's selector does.
            clash = traits[i]["equipped"];
            j = 0;
            while(!clash && j < taken.length)
            {
               if(taken[j]["conflicts"].indexOf(traits[i]["id"]) >= 0 || traits[i]["conflicts"].indexOf(taken[j]["id"]) >= 0) { clash = true; }
               j = j + 1;
            }
            if(!clash) { labels.push(traits[i]["title"]); values.push(traits[i]["id"]); }
            i = i + 1;
         }
         this.A11yGuideList("traitpick",String(group["title"]),
            labels.length > 0 ? "Choose a trait. Traits that clash with ones already chosen are left out." : "No more traits of this kind fit with the ones already chosen.",labels,values);
      }

      public function A11yGuideTraitRemoveDialog() : void
      {
         var equipped:Array = this.A11yGuideEquipped(this.A11yGuideTraitScan());
         var labels:Array = new Array();
         var values:Array = new Array();
         var i:int = 0;
         while(i < equipped.length) { labels.push(equipped[i]["title"]); values.push(equipped[i]["id"]); i = i + 1; }
         this.A11yGuideList("traitremove","Remove a trait","Choose the trait to remove.",labels,values);
      }

      // Aspiration: CAS's own categories and tracks
      // (CasGetAspirationCategories, CasGetAspirationTracksByCategory,
      // AspirationTrackStaticData) and SetSimAspiration {uid}.
      public function A11yGuideAspirationCategories() : void
      {
         var raw:Array = CommunicationManager.CallGameService("CasGetAspirationCategories") as Array;
         var labels:Array = new Array();
         var values:Array = new Array();
         var i:int = 0;
         if(raw == null || raw.length == 0) { this.mA11yGuideAspiration = ""; this.A11yGuideSummary(); return; }
         raw = raw.slice();
         // Order as CAS does (ui_sort_order); a plain insertion sort.
         var k:int = 1;
         var m:int = 0;
         var held:Object = null;
         while(k < raw.length)
         {
            held = raw[k];
            m = k - 1;
            while(m >= 0 && int(raw[m]["ui_sort_order"]) > int(held["ui_sort_order"])) { raw[m + 1] = raw[m]; m = m - 1; }
            raw[m + 1] = held;
            k = k + 1;
         }
         while(i < raw.length) { labels.push(this.A11yGuideText(raw[i]["name"])); values.push(raw[i]["uid"]); i = i + 1; }
         this.A11yGuideList("aspcat","Step 5: Aspiration",
            "An aspiration is your Sim's life goal. It gives them goals to work towards and rewards. Choose a kind first.",labels,values);
      }

      public function A11yGuideAspirationTracks(category:Object) : void
      {
         var raw:Array = CommunicationManager.CallGameService("CasGetAspirationTracksByCategory",{"categoryId":category}) as Array;
         var tracks:Object = getDefinitionByName("gamedata.Gameplay.shared.definitions.AspirationTrackStaticData");
         var track:Object = null;
         var label:String = "";
         var labels:Array = new Array();
         var values:Array = new Array();
         var i:int = 0;
         while(raw != null && i < raw.length)
         {
            track = tracks["GetTrackData"](String(raw[i]["id"]));
            if(track != null && !track["isHiddenUnlockable"])
            {
               label = this.A11yGuideText(track["display_text"]);
               labels.push(label);
               values.push({"uid":String(track["uid"]),"label":label});
            }
            i = i + 1;
         }
         this.A11yGuideList("asptrack","Choose an aspiration","Choose your Sim's aspiration.",labels,values);
      }

      public function A11yGuideSummary() : void
      {
         var equipped:Array = this.A11yGuideEquipped(this.A11yGuideTraitScan());
         var names:Array = new Array();
         var i:int = 0;
         while(i < equipped.length) { names.push(equipped[i]["title"]); i = i + 1; }
         this.mA11yGuideList = ["done","name","age","traits","aspiration","extras"];
         this.A11yGuideDialog("summary","Your Sim",
            this.A11yGuideSimName() + ". Traits: " + (names.length > 0 ? names.join(", ") : "none") + ". Aspiration: " +
            (this.mA11yGuideAspiration != "" ? this.mA11yGuideAspiration : "none") + ".",
            ["Done","Change the name","Change age or gender","Change traits","Change aspiration","Voice and walk style (optional)","Back"]);
      }

// Home: leave Create a Sim the way EA's Play button does, then the world
      // and the lot as button dialogs, then EA's own move-in panel.
      //   CASNavigationMain.EnterGame: CasApplyNameFields, CasGetHouseholdExchangeData
      //   CASHouseholdSummaryMain: CasSaveHouseholdToTray, ExchangeItemSaved,
      //     EnterGame {name}, ShowTransitionScreen CAS_TO_NHD_MAP (31)
      //   GEWorldSelectionMain: TransitionToNeighborhoodMap {NeighborhoodData}
      //   NeighborhoodMap.OnConfirmModeOp: ConfirmModeOp {lotData}
      //   MoveInPanel: ddInOptions (0 unfurnished, 1 furnished), btnOkay
      // After a new family moves in, NeighborhoodMap plays the lot itself.
      // Optional extras, as CAS's age and gender pane offers them:
      // AgeGenderPane voice buttons (GetVoicesDataForAgeSpecies,
      // SetSimVoiceActor with the 0-based button index), its pitch slider
      // (SetSimVoicePitch {value, slider_mouse_up} within the voice's
      // minPitch..maxPitch) and its walk style panel (CasGetWalkCycleTraits,
      // CasSetWalkCycleTrait {traitID}; not for children or younger).
      public function A11yGuideVoices() : Array
      {
         var info:Object = this.A11yGuideSimInfo();
         var raw:Array = CommunicationManager.CallGameService("GetVoicesDataForAgeSpecies",
            {"species":int(info["speciesType"]),"age":int(CommunicationManager.CallGameService("GetSimAge"))}) as Array;
         return raw != null ? raw : new Array();
      }

      public function A11yGuideVoiceName(voices:Array, actor:int) : String
      {
         if(actor < 1 || actor > voices.length) { return "not set"; }
         return this.A11yGuideText(voices[actor - 1]["tooltip"]);
      }

      public function A11yGuideWalkStyles() : Array
      {
         var info:Object = this.A11yGuideSimInfo();
         var age:int = int(CommunicationManager.CallGameService("GetSimAge"));
         var raw:Array = null;
         if([1,2,4,128].indexOf(age) >= 0) { return null; }
         raw = CommunicationManager.CallGameService("CasGetWalkCycleTraits",{"simId":String(info["simId"])}) as Array;
         return raw != null ? raw : new Array();
      }

      public function A11yGuideExtrasDialog() : void
      {
         var info:Object = this.A11yGuideSimInfo();
         var voices:Array = this.A11yGuideVoices();
         var walks:Array = this.A11yGuideWalkStyles();
         var walk:String = "default";
         var labels:Array = new Array();
         var values:Array = new Array();
         var i:int = 0;
         while(walks != null && i < walks.length)
         {
            if(walks[i]["equipped"] == true) { walk = this.A11yGuideText(walks[i]["title"]); }
            i = i + 1;
         }
         if(voices.length > 0)
         {
            labels.push("Voice: " + this.A11yGuideVoiceName(voices,int(info["voiceActor"])));
            values.push("voice");
            labels.push("Voice pitch");
            values.push("pitch");
         }
         labels.push(walks == null ? "Walk style: not for children" : "Walk style: " + walk);
         values.push("walk");
         this.A11yGuideList("extras","Voice and walk style",
            "These are optional. Change them now, or choose Back to return to your Sim's summary. You can also change them later in Create a Sim.",labels,values);
      }

      public function A11yGuideVoiceDialog() : void
      {
         var info:Object = this.A11yGuideSimInfo();
         var voices:Array = this.A11yGuideVoices();
         var labels:Array = new Array();
         var values:Array = new Array();
         var i:int = 0;
         while(i < voices.length)
         {
            labels.push(this.A11yGuideText(voices[i]["tooltip"]) + (int(info["voiceActor"]) == i + 1 ? " (now)" : ""));
            values.push(i);
            i = i + 1;
         }
         this.A11yGuideList("voice","Voice",
            "Choose a voice to give it to your Sim. Your Sim usually says something in that voice, so you can try each one. Choose Back when you are happy.",labels,values);
      }

      public function A11yGuidePitchDialog() : void
      {
         var info:Object = this.A11yGuideSimInfo();
         var voices:Array = this.A11yGuideVoices();
         var actor:int = int(info["voiceActor"]);
         var low:Number = 0;
         var high:Number = 0;
         var now:Number = Number(info["voicePitch"]);
         var names:Array = ["Lowest","Lower","Middle","Higher","Highest"];
         var labels:Array = new Array();
         var values:Array = new Array();
         var value:Number = 0;
         var nearest:int = 0;
         var i:int = 0;
         if(actor < 1 || actor > voices.length) { actor = 1; }
         if(voices.length == 0) { this.A11yGuideExtrasDialog(); return; }
         low = Number(voices[actor - 1]["minPitch"]);
         high = Number(voices[actor - 1]["maxPitch"]);
         if(!isFinite(low) || !isFinite(high) || high < low) { low = -1; high = 1; }
         while(i < 5)
         {
            value = low + (high - low) * i / 4;
            if(Math.abs(value - now) < Math.abs(low + (high - low) * nearest / 4 - now)) { nearest = i; }
            values.push(value);
            i = i + 1;
         }
         i = 0;
         while(i < 5) { labels.push(names[i] + (i == nearest ? " (now)" : "")); i = i + 1; }
         this.A11yGuideList("pitch","Voice pitch",
            "Choose how high or low your Sim's voice is. Your Sim usually says something at that pitch. Choose Back when you are happy.",labels,values);
      }

      public function A11yGuideWalkDialog() : void
      {
         var walks:Array = this.A11yGuideWalkStyles();
         var labels:Array = new Array();
         var values:Array = new Array();
         var i:int = 0;
         if(walks == null)
         {
            this.A11yGuideList("walk","Walk style","Children, toddlers and babies walk the way all children do, so they have no walk style. Choose Back.",labels,values);
            return;
         }
         while(i < walks.length)
         {
            labels.push(this.A11yGuideText(walks[i]["title"]) + (walks[i]["equipped"] == true ? " (now)" : ""));
            values.push(String(walks[i]["id"]));
            i = i + 1;
         }
         this.A11yGuideList("walk","Walk style","Choose how your Sim walks. Choose Back when you are happy.",labels,values);
      }

      public function A11yGuideReady() : void
      {
         var others:Array = this.A11yGuideRelations();
         var labels:Array = ["Find a home","Add another Sim"];
         var values:Array = ["home","add"];
         var names:Array = [this.A11yGuideSimName()];
         var i:int = 0;
         this.A11yGuideRemember();
         while(i < others.length) { names.push(this.A11yGuideOtherName(others[i])); i = i + 1; }
         if(others.length > 0)
         {
            labels.push("Set relationships");
            values.push("relations");
            labels.push("Change another Sim");
            values.push("switch");
         }
         labels.push("Change how my Sims look first");
         values.push("looks");
         this.A11yGuideList("ready",names.length > 1 ? "Your household is ready" : "Your Sim is ready",
            (names.length > 1 ? "Your household: " + names.join(", ") + ". " : "") +
            "Next, choose where to live: a world, then a home. Or add another Sim to the household. Or change how your Sims look first: the guide closes, and the full Create a Sim screen is yours. Its Play button also leads to choosing a home.",
            labels,values);
      }

      // Household: CASSimSelectorMain / AddSimMenu (CasAddSim, CasSelectSim)
      // and RelationshipsPane (CasGetHouseholdRelationsForCurrentSim,
      // CasAddRelationship, CasSetTropeToRelationshipWith). The guide keeps
      // the names it has seen, by Sim ID, to name the other Sims.
      public function A11yGuideRemember() : void
      {
         var info:Object = this.A11yGuideSimInfo();
         if(info["simId"] != undefined && info["simId"] != null) { this.mA11yGuideNames[String(info["simId"])] = this.A11yGuideSimName(); }
      }

      public function A11yGuideRelations() : Array
      {
         var raw:Array = CommunicationManager.CallGameService("CasGetHouseholdRelationsForCurrentSim") as Array;
         return raw != null ? raw : new Array();
      }

      public function A11yGuideOtherName(other:Object) : String
      {
         var id:String = String(other["simId"]);
         if(this.mA11yGuideNames[id] != undefined) { return String(this.mA11yGuideNames[id]); }
         return "Sim " + (int(other["simIndex"]) + 1);
      }

      public function A11yGuideRelationName(rel:int, mine:int, theirs:int, otherId:String) : String
      {
         var relClass:Object = getDefinitionByName("widgets.shared.constants.SimRelationship");
         var key:Object = relClass["GetRelationshipName"](rel,mine,theirs);
         if(key == null) { return rel == int(relClass["NONE"]) ? "No relation" : "Relationship " + rel; }
         return String(key["toString"]({"simId":otherId}));
      }

      public function A11yGuideAddSim() : void
      {
         var relClass:Object = getDefinitionByName("widgets.shared.constants.SimRelationship");
         this.A11yGuideRemember();
         this.A11yGuideTraitsClose();
         this.mA11yGuideAddFrom = String(this.A11yGuideSimInfo()["simId"]);
         // AddSimMenu.ActionAddSim for a human: OccultTypes.OCCULT_HUMAN (1),
         // Species.TYPE_HUMAN (1), CreateSimOps.SIMOPFLAG_CREATE_FROM_SCRATCH (1).
         CommunicationManager.CallGameService("CasAddSim",{"relSimId":"0","relationship":int(relClass["NONE"]),"species":1,"occultType":1,"action":1});
         this.mA11yGuideAspiration = "";
         this.mA11yGuideNewSim = true;
         this.A11yPostToPython("a11y.mark","guide-sim-added");
         this.A11yGuideSay("Adding a new Sim.");
         this.mA11yGuideState = "adding";
         this.mA11yGuideEditAt = getTimer();
      }

      public function A11yGuideRelationsDialog() : void
      {
         var others:Array = this.A11yGuideRelations();
         var labels:Array = new Array();
         var info:Object = this.A11yGuideSimInfo();
         var i:int = 0;
         while(i < others.length)
         {
            labels.push(this.A11yGuideOtherName(others[i]) + ": " +
               this.A11yGuideRelationName(int(others[i]["currentRelation"]),int(info["speciesType"]),int(others[i]["speciesType"]),String(others[i]["simId"])));
            i = i + 1;
         }
         this.A11yGuideList("relations","Relationships for " + this.A11yGuideSimName(),
            "Choose a Sim to set how " + this.A11yGuideSimName() + " is related to them. Choose Back when you are done.",labels,others);
      }

      public function A11yGuideRelationPickDialog(other:Object) : void
      {
         var info:Object = this.A11yGuideSimInfo();
         var options:Array = other["relOptions"] as Array;
         var labels:Array = new Array();
         var values:Array = new Array();
         var rel:int = 0;
         var i:int = 0;
         while(options != null && i < options.length)
         {
            rel = int(options[i]);
            labels.push(this.A11yGuideRelationName(rel,int(info["speciesType"]),int(other["speciesType"]),String(other["simId"])) +
               (rel == int(other["currentRelation"]) ? " (now)" : ""));
            values.push({"other":other,"rel":rel});
            i = i + 1;
         }
         this.A11yGuideList("relpick",this.A11yGuideOtherName(other),
            other["canModify"] == false ? "This relationship cannot be changed." : "Choose what " + this.A11yGuideOtherName(other) + " is to " + this.A11yGuideSimName() + ".",
            other["canModify"] == false ? new Array() : labels,other["canModify"] == false ? new Array() : values);
      }

      public function A11yGuideSetRelation(choice:Object) : void
      {
         var info:Object = this.A11yGuideSimInfo();
         var other:Object = choice["other"];
         var tropes:int = 0;
         var i:int = 0;
         CommunicationManager.CallGameService("CasAddRelationship",{"simIdA":String(info["simId"]),"simIdB":String(other["simId"]),"relType":int(choice["rel"])});
         // RelationshipsPane clears both trope kinds after a new relationship.
         try { tropes = int(getDefinitionByName("gamedata.CAS.Relationships.SimTropeItem")["ALL_TROPE_TYPES"]); }
         catch(e:Error) { tropes = 0; }
         while(i < tropes)
         {
            CommunicationManager.CallGameService("CasSetTropeToRelationshipWith",{"simIdA":String(info["simId"]),"simIdB":String(other["simId"]),"tropeId":"0","tropeType":String(i)});
            i = i + 1;
         }
         this.A11yPostToPython("a11y.mark","guide-relation-" + int(choice["rel"]));
         this.A11yGuideRelationsDialog();
      }

      public function A11yGuideSwitchDialog() : void
      {
         var others:Array = this.A11yGuideRelations();
         var labels:Array = new Array();
         var i:int = 0;
         while(i < others.length) { labels.push(this.A11yGuideOtherName(others[i])); i = i + 1; }
         this.A11yGuideList("switch","Change another Sim","Choose the Sim to change. The guide shows their summary.",labels,others);
      }

      public function A11yGuideSwitchTo(other:Object) : void
      {
         this.A11yGuideRemember();
         this.A11yGuideTraitsClose();
         if(CommunicationManager.CallGameService("CasSelectSim",int(other["simIndex"])) != true)
         {
            this.A11yGuideSay("The game did not switch Sims.");
            this.A11yGuideReady();
            return;
         }
         this.mA11yGuideAspiration = "";
         this.mA11yGuideNewSim = false;
         this.A11yGuideSummary();
      }

      public function A11yGuideHomeStart() : void
      {
         var age:int = int(CommunicationManager.CallGameService("GetSimAge"));
         var others:Array = this.A11yGuideRelations();
         var grown:Boolean = age == 16 || age == 32 || age == 64;
         var rude:Object = null;
         var data:Object = null;
         var i:int = 0;
         while(i < others.length) { if([16,32,64].indexOf(int(others[i]["age"])) >= 0) { grown = true; } i = i + 1; }
         this.mA11yGuideList = new Array();
         if(!grown)
         {
            this.A11yGuideDialog("adult","A grown-up is needed",
               "A household needs at least one young adult, adult or elder to live on its own. Choose Change age to pick an older age.",
               ["Change age","Back"]);
            return;
         }
         rude = CommunicationManager.CallGameService("CASCheckProfanityOnSimNames",null);
         if(rude != null && rude["simId"] != undefined && rude["simId"] != null && String(rude["simId"]) != "0")
         {
            this.A11yGuideDialog("badname","Choose another name",
               "The game does not allow this name. Choose Change the name to pick another one.",
               ["Change the name","Back"]);
            return;
         }
         CommunicationManager.SendUIMessage("CASHidePersonalityAndGeneticsPanels",null);
         CommunicationManager.SendUIMessage("CASHideCustomizer",null);
         CommunicationManager.SendUIMessage("CASResetGhostToggle",null);
         CommunicationManager.SendUIMessage("CASResetWingToggle",null);
         if(CommunicationManager.CallUIService("IsWidgetVisible","CASGeneticsPane") == true || CommunicationManager.CallUIService("CasApplyNameFields",false) != true)
         {
            this.A11yGuideHomeError("The game could not finish your Sim yet.");
            return;
         }
         data = CommunicationManager.CallGameService("CasGetHouseholdExchangeData",{"bValidateExistingSimTraits":false});
         if(data == null)
         {
            this.A11yGuideHomeError("The game could not finish your household yet.");
            return;
         }
         this.mA11yGuideHousehold = data["name"] != undefined && data["name"] != null ? String(data["name"]) : "";
         this.A11yGuideDialog("household","Your household",
            "Your household is called " + (this.mA11yGuideHousehold != "" ? "the " + this.mA11yGuideHousehold + " household" : "by your Sim's last name") +
            ". Choose Save and find a home. The game saves your household to your library and opens the world map. This takes a moment.",
            ["Save and find a home","Back"]);
      }

      public function A11yGuideHomeError(text:String) : void
      {
         this.mA11yGuideList = new Array();
         this.A11yGuideDialog("homeerror","Not ready yet",
            text + " Choose Back to check your Sim, or close the guide and use the Play button in Create a Sim.",
            ["Back","Close the guide"]);
      }

      public function A11yGuideHomeSave() : void
      {
         this.mA11yGuidePhase = "saving";
         this.mA11yGuidePhaseAt = getTimer();
         this.A11yPostToPython("a11y.mark","guide-home-save");
         CommunicationManager.AddMessageListenerByName("ExchangeItemSaved",this.A11yGuideHomeSaved,"A11yGuide");
         this.A11yGuideSay("Saving your household.");
         CommunicationManager.CallGameService("CasSaveHouseholdToTray",{"name":this.mA11yGuideHousehold,"description":"","hashtags":"","isTemp":false,"templateId":"0"});
      }

      public function A11yGuideHomeSaved(data:Object) : void
      {
         try
         {
            CommunicationManager.RemoveMessageListenerByName("ExchangeItemSaved",this.A11yGuideHomeSaved,"A11yGuide");
            if(this.mA11yGuidePhase != "saving") { return; }
            this.A11yGuideHomeEnter(data != null && data["itemId"] != undefined && String(data["itemId"]) != "0");
         }
         catch(e:Error) { this.mA11yGuidePhase = ""; this.A11yPostToPython("a11y.mark","guide-error-" + e.message); }
      }

      public function A11yGuideHomeEnter(saved:Boolean) : void
      {
         this.mA11yGuideFresh = new Object();
         this.mA11yGuidePhase = "entering";
         this.mA11yGuidePhaseAt = getTimer();
         this.mA11yGuideReadyAt = 0;
         this.A11yGuideTraitsClose();
         this.A11yPostToPython("a11y.mark","guide-home-enter-" + (saved ? "saved" : "unsaved"));
         CommunicationManager.CallGameService("EnterGame",{"name":this.mA11yGuideHousehold,"description":""});
         CommunicationManager.SendUIMessage("ShowTransitionScreen",{"mode":31});
         this.A11yGuideSay("Going to the world map. This takes a moment.");
      }

      // Runs every frame (throttled) while the guide is past Create a Sim.
      public function A11yGuideHomeFrame(now:int) : void
      {
         var world:Object = null;
         var panel:Object = null;
         var phase:String = this.mA11yGuidePhase;
         if(phase == "saving")
         {
            if(now - this.mA11yGuidePhaseAt > 15000)
            {
               CommunicationManager.RemoveMessageListenerByName("ExchangeItemSaved",this.A11yGuideHomeSaved,"A11yGuide");
               this.A11yGuideHomeEnter(false);
            }
            return;
         }
         if(phase == "entering")
         {
            if(now - this.mA11yGuidePhaseAt > 180000) { this.mA11yGuidePhase = ""; this.A11yPostToPython("a11y.mark","guide-home-timeout"); return; }
            if(this.mA11yManagedDialog != null) { this.mA11yGuideReadyAt = 0; return; }
            if(this.A11ySeasonScope() != null)
            {
               if(this.mA11yGuideReadyAt == 0) { this.mA11yGuideReadyAt = now; return; }
               if(now - this.mA11yGuideReadyAt < 1000) { return; }
               this.A11yGuideSeasonDialog();
               return;
            }
            world = this.A11yLoadedWidget("GameEntryWorldSelection");
            if(!this.A11yIsLive(world as DisplayObject) || !this.A11yIsLive(world["mcWSGridView"] as DisplayObject) || world["mouseChildren"] == false || this.A11yGuideWorlds().length == 0)
            {
               this.mA11yGuideReadyAt = 0;
               return;
            }
            if(this.mA11yGuideReadyAt == 0) { this.mA11yGuideReadyAt = now; return; }
            if(now - this.mA11yGuideReadyAt < 1500) { return; }
            this.A11yGuideWorldDialog();
            return;
         }
         if(phase == "map")
         {
            if(this.mA11yGuideMapAt != 0 && now - this.mA11yGuideMapAt > 1500 || now - this.mA11yGuidePhaseAt > 20000)
            {
               CommunicationManager.RemoveMessageListenerByName("NhdMapLoaded",this.A11yGuideMapLoaded,"A11yGuide");
               this.A11yGuideLotsDialog();
            }
            return;
         }
         if(phase == "buying")
         {
            panel = this.A11yGuideMovePanel();
            if(panel != null && now - this.mA11yGuidePhaseAt > 800) { this.A11yGuideMoveIn(panel); }
            else if(panel == null && now - this.mA11yGuidePhaseAt > 10000)
            {
               this.mA11yGuideList = new Array();
               this.A11yGuideDialog("nopanel","The move-in window did not open",
                  "The game did not open the move-in window for this home. Choose another home, or close the guide and use the map with Tab.",
                  ["Choose another home","Close the guide"]);
            }
            return;
         }
         if(phase == "moved")
         {
            world = this.A11yLoadedWidget("GameEntryWorldSelection");
            if(!this.A11yIsLive(world as DisplayObject))
            {
               // The world map is gone: the game is loading the lot.
               this.mA11yGuidePhase = "";
               this.A11yPostToPython("a11y.mark","guide-home-playing");
               return;
            }
            if(this.A11yGuideMovePanel() == null && now - this.mA11yGuidePhaseAt > 25000) { this.A11yGuidePlayDialog(); }
         }
      }

      public function A11yGuideSeasonDialog() : void
      {
         this.mA11yGuidePhase = "season";
         this.mA11yGuideList = new Array();
         this.A11yGuideDialog("season","Choose a season",
            "Choose the season your game starts in. Spring is a good first choice.",
            ["Spring","Summer","Fall","Winter"]);
      }

      // Worlds a new family can live in: player-facing, not vacation worlds.
      public function A11yGuideWorlds() : Array
      {
         var stateClass:Object = getDefinitionByName("gamedata.GameEntry.shared.NeighborhoodStateData");
         var regionClass:Object = getDefinitionByName("gamedata.GameEntry.shared.RegionDescription");
         var all:Object = stateClass["AllNeighborhoodData"];
         var out:Array = new Array();
         var seen:Object = new Object();
         var key:String = null;
         var nhd:Object = null;
         var region:Object = null;
         var regionId:String = "";
         var homes:Array = null;
         var funds:Number = this.A11yGuideFunds();
         var fit:int = 0;
         var empty:int = 0;
         var i:int = 0;
         if(all == null) { return out; }
         for(key in all)
         {
            nhd = all[key];
            if(nhd == null || nhd["IsPlayerFacingNeighborhood"] != true) { continue; }
            regionId = String(nhd["regionId"]);
            if(seen[regionId] == true) { continue; }
            seen[regionId] = true;
            region = regionClass["GetRegionDescription"](regionId);
            if(region == null || region["bVacationWorld"] == true) { continue; }
            homes = this.A11yGuideHomes(regionId);
            fit = 0;
            empty = 0;
            i = 0;
            while(i < homes.length)
            {
               if(homes[i]["empty"]) { empty = empty + 1; }
               else if(homes[i]["cheapest"] <= funds) { fit = fit + 1; }
               i = i + 1;
            }
            out.push({"label":this.A11yGuideText(region["regionName"]) + ": " + (homes.length == 0 ? "no homes for sale" :
               fit + (fit == 1 ? " house" : " houses") + " you can afford" + (empty > 0 ? ", " + empty + (empty == 1 ? " empty lot" : " empty lots") : "")),
               "nhd":nhd,"regionId":regionId,"homes":homes.length});
         }
         return out;
      }

      public function A11yGuideFunds() : Number
      {
         var info:Object = CommunicationManager.CallGameService("GetFamilyInfo");
         if(info != null && info["familyFunds"] != undefined) { return Number(info["familyFunds"]); }
         return 0;
      }

      public function A11yGuideMoney(value:Number) : String
      {
         var digits:String = String(Math.round(Math.abs(value)));
         var out:String = "";
         while(digits.length > 3) { out = "," + digits.substr(digits.length - 3) + out; digits = digits.substr(0,digits.length - 3); }
         return (value < 0 ? "minus " : "") + digits + out + " simoleons";
      }

      // Empty residential lots (NeighborhoodLotData.VACANT_LOT) in a world,
      // cheapest first, with the prices MoveInPanel charges.
      public function A11yGuideHomes(regionId:String) : Array
      {
         var stateClass:Object = getDefinitionByName("gamedata.GameEntry.shared.NeighborhoodStateData");
         var all:Object = stateClass["AllNeighborhoodData"];
         var out:Array = new Array();
         var key:String = null;
         var nhd:Object = null;
         var lots:Array = null;
         var lot:Object = null;
         var entry:Object = null;
         var lotClass:Class = null;
         var raw:Object = null;
         var zone:String = "";
         var i:int = 0;
         var j:int = 0;
         if(all == null) { return out; }
         try { lotClass = getDefinitionByName("gamedata.GameEntry.Neighborhood.NeighborhoodLotData") as Class; }
         catch(e:Error) { lotClass = null; }
         for(key in all)
         {
            nhd = all[key];
            if(nhd == null || String(nhd["regionId"]) != regionId) { continue; }
            lots = nhd["lots"] as Array;
            i = 0;
            while(lots != null && i < lots.length)
            {
               lot = lots[i];
               i = i + 1;
               if(lot == null || int(lot["mLotType"]) != 0 || lot["IsInPlex"] == true || lot["IsMultiUnitBuilding"] == true) { continue; }
               // The cached world data can lack house and furniture prices;
               // refresh each lot once from the game (NeighborhoodMap does the
               // same with GetNeighborhoodLotData), so the move-in panel gets
               // the same object with its furnishings.
               zone = String(lot["zoneInstanceId"]);
               if(lotClass != null && this.mA11yGuideFresh[zone] != true)
               {
                  this.mA11yGuideFresh[zone] = true;
                  try
                  {
                     raw = CommunicationManager.CallGameService("GetNeighborhoodLotData",zone);
                     if(raw != null) { lot["UpdateZoneData"](new lotClass(raw)); }
                  }
                  catch(e2:Error) { }
               }
               entry = {"lot":lot,"name":String(lot["lotName"]),"area":String(nhd["name"]),"empty":lot["IsEmpty"] == true,"furnished":lot["IsFurnished"] == true,
                  "full":Number(lot["TotalPrice"]),"bare":Number(lot["UnfurnishedPrice"]),"land":Number(lot["LotPrice"]),
                  "beds":int(lot["numBeds"]),"baths":int(lot["numBaths"])};
               entry["cheapest"] = entry["empty"] ? entry["land"] : entry["bare"];
               // Houses first, cheapest first; empty lots (nothing built) last.
               entry["order"] = (entry["empty"] ? 1000000000 : 0) + entry["cheapest"];
               j = out.length;
               while(j > 0 && out[j - 1]["order"] > entry["order"]) { j = j - 1; }
               out.splice(j,0,entry);
            }
         }
         return out;
      }

      public function A11yGuideWorldDialog() : void
      {
         var worlds:Array = this.A11yGuideWorlds();
         var labels:Array = new Array();
         var i:int = 0;
         this.mA11yGuidePhase = "world";
         while(i < worlds.length) { labels.push(worlds[i]["label"]); i = i + 1; }
         this.A11yGuideList("world","Choose a world",
            "Your household has " + this.A11yGuideMoney(this.A11yGuideFunds()) + ". Choose the world your Sims will live in. Each world says how many houses you can afford, and how many empty lots it has.",
            labels,worlds);
      }

      public function A11yGuideGoToWorld(world:Object) : void
      {
         this.mA11yGuideRegion = String(world["regionId"]);
         this.mA11yGuidePhase = "map";
         this.mA11yGuidePhaseAt = getTimer();
         this.mA11yGuideMapAt = 0;
         this.A11yPostToPython("a11y.mark","guide-home-world-" + this.mA11yGuideRegion);
         CommunicationManager.AddMessageListenerByName("NhdMapLoaded",this.A11yGuideMapLoaded,"A11yGuide");
         CommunicationManager.SendUIMessage("TransitionToNeighborhoodMap",world["nhd"]);
         this.A11yGuideSay("Opening the map.");
      }

      public function A11yGuideMapLoaded(data:Object = null) : void
      {
         this.mA11yGuideMapAt = getTimer();
      }

      public function A11yGuideHomeLabel(home:Object) : String
      {
         return home["name"] + ", " + home["area"] + ". " + (home["empty"] ? "Empty lot with no house, you build it yourself, " + this.A11yGuideMoney(home["land"]) :
            home["beds"] + " bedrooms, " + home["baths"] + " bathrooms, " + (home["furnished"] ? "furnished " + this.A11yGuideMoney(home["full"]) : this.A11yGuideMoney(home["bare"]))) +
            (home["cheapest"] > this.A11yGuideFunds() ? ". Too expensive" : "");
      }

      public function A11yGuideLotsDialog() : void
      {
         var homes:Array = this.A11yGuideHomes(this.mA11yGuideRegion);
         var labels:Array = new Array();
         var i:int = 0;
         this.mA11yGuidePhase = "lots";
         while(i < homes.length) { labels.push(this.A11yGuideHomeLabel(homes[i])); i = i + 1; }
         this.A11yGuideList("lots","Choose a home",
            homes.length > 0 ? "Your household has " + this.A11yGuideMoney(this.A11yGuideFunds()) + ". Houses come first, cheapest first. Empty lots, where you build the house yourself, come last. Choose one to see its options." :
            "No homes are for sale in this world. Choose Back to pick another world.",labels,homes);
      }

      public function A11yGuideFurnishDialog(home:Object) : void
      {
         var funds:Number = this.A11yGuideFunds();
         var labels:Array = new Array();
         var values:Array = new Array();
         this.mA11yGuideLot = home;
         if(home["empty"])
         {
            labels.push("Buy this empty lot for " + this.A11yGuideMoney(home["land"]) + ", leaving " + this.A11yGuideMoney(funds - home["land"]));
            values.push({"mode":-1,"price":home["land"]});
         }
         else
         {
            if(home["furnished"])
            {
               labels.push("Furnished: " + this.A11yGuideMoney(home["full"]) + ", leaving " + this.A11yGuideMoney(funds - home["full"]));
               values.push({"mode":1,"price":home["full"]});
            }
            labels.push("Unfurnished: " + this.A11yGuideMoney(home["bare"]) + ", leaving " + this.A11yGuideMoney(funds - home["bare"]));
            values.push({"mode":0,"price":home["bare"]});
         }
         this.A11yGuideList("furnish",String(home["name"]),
            this.A11yGuideHomeLabel(home) + ". Your household has " + this.A11yGuideMoney(funds) + "." +
            (home["furnished"] ? " Furnished comes with furniture, so your Sim can start right away." : "") + " Choose how to buy it.",labels,values);
      }

      public function A11yGuideBuy(choice:Object) : void
      {
         if(Number(choice["price"]) > this.A11yGuideFunds())
         {
            this.mA11yGuideList = new Array();
            this.A11yGuideDialog("toodear","Not enough money",
               "Your household cannot afford this. Choose another option or another home.",["OK"]);
            return;
         }
         this.mA11yGuideFurnish = int(choice["mode"]);
         this.mA11yGuidePhase = "buying";
         this.mA11yGuidePhaseAt = getTimer();
         this.A11yPostToPython("a11y.mark","guide-home-lot-" + String(this.mA11yGuideLot["lot"]["zoneInstanceId"]) + "-mode-" + this.mA11yGuideFurnish);
         CommunicationManager.SendUIMessage("ConfirmModeOp",{"lotData":this.mA11yGuideLot["lot"]});
      }

      public function A11yGuideMovePanel() : Object
      {
         var widget:Object = this.A11yLoadedWidget("GameEntryMovePanel");
         var child:DisplayObject = null;
         var i:int = 0;
         if(!this.A11yIsLive(widget as DisplayObject)) { return null; }
         while(i < widget["numChildren"])
         {
            child = widget["getChildAt"](i) as DisplayObject;
            if(getQualifiedClassName(child) == "widgets.GameEntry.MovePanel.controls::MoveInPanel" && this.A11yIsLive(child)) { return child; }
            i = i + 1;
         }
         return null;
      }

      // Set the furnishing choice the way the dropdown's own list does
      // (select, then ITEM_SELECTED so the panel reprices), then Purchase.
      public function A11yGuideMoveIn(panel:Object) : void
      {
         var dropdown:Object = panel["ddInOptions"];
         var ext:Object = null;
         var eventClass:Class = null;
         var okay:DisplayObject = panel["btnOkay"] as DisplayObject;
         this.mA11yGuidePhase = "moved";
         this.mA11yGuidePhaseAt = getTimer();
         if(this.mA11yGuideFurnish >= 0 && dropdown != null && dropdown["visible"] == true)
         {
            ext = dropdown["DropdownExt"];
            ext["SetSelectedFromMenuItemData"](this.mA11yGuideFurnish);
            eventClass = getDefinitionByName("olympus.gui.events.DropdownEvent") as Class;
            dropdown["dispatchEvent"](new eventClass(eventClass["ITEM_SELECTED"],ext["SelectedData"]));
         }
         if(okay == null || okay["enabled"] == false)
         {
            this.mA11yGuidePhase = "lots";
            this.A11yClickControl(panel["btnClose"] as DisplayObject);
            this.mA11yGuideList = new Array();
            this.A11yGuideDialog("cantbuy","This home cannot be bought",
               "The move-in window would not let your household buy this home. Choose another home.",["Choose another home"]);
            return;
         }
         this.A11yPostToPython("a11y.mark","guide-home-purchase");
         this.A11yClickControl(okay);
         this.A11yGuideSay("Buying your home. The game then loads it so you can play.");
      }

      public function A11yGuidePlayDialog() : void
      {
         this.mA11yGuidePhase = "play";
         this.mA11yGuideList = new Array();
         this.A11yGuideDialog("play","Your home is ready","Your household has moved in. Choose Play to start.",["Play"]);
      }

      public function A11yGuidePlay() : void
      {
         var info:Object = CommunicationManager.CallGameService("GetFamilyInfo");
         this.mA11yGuidePhase = "moved";
         this.mA11yGuidePhaseAt = getTimer();
         if(info == null) { return; }
         this.A11yPostToPython("a11y.mark","guide-home-play");
         CommunicationManager.CallGameService("PlayHousehold",{"householdId":String(info["familyId"]),"zoneInstanceId":String(info["familyLotId"])});
      }

      public function A11yGuideHomeAnswer(step:String, index:int, picked:Object) : void
      {
         var scope:Object = null;
         var names:Array = ["btnSpring","btnSummer","btnFall","btnWinter"];
         if(step == "ready")
         {
            if(picked == "home") { this.A11yGuideHomeStart(); }
            else if(picked == "add") { this.A11yGuideAddSim(); }
            else if(picked == "relations") { this.A11yGuideRelationsDialog(); }
            else if(picked == "switch") { this.A11yGuideSwitchDialog(); }
            else if(picked == "looks") { this.A11yGuideFinish(); }
            else { this.A11yGuideSummary(); }
         }
         else if(step == "relations")
         {
            if(picked != null) { this.A11yGuideRelationPickDialog(picked); }
            else { this.A11yGuideReady(); }
         }
         else if(step == "relpick")
         {
            if(picked != null) { this.A11yGuideSetRelation(picked); }
            else { this.A11yGuideRelationsDialog(); }
         }
         else if(step == "switch")
         {
            if(picked != null) { this.A11yGuideSwitchTo(picked); }
            else { this.A11yGuideReady(); }
         }
         else if(step == "adult")
         {
            if(index == 0) { this.A11yGuideAgeDialog(); }
            else { this.A11yGuideReady(); }
         }
         else if(step == "badname")
         {
            if(index == 0) { this.A11yGuideNameDialog(); }
            else { this.A11yGuideReady(); }
         }
         else if(step == "homeerror")
         {
            if(index == 1) { this.A11yGuideFinish(); }
            else { this.A11yGuideSummary(); }
         }
         else if(step == "household")
         {
            if(index == 0) { this.A11yGuideHomeSave(); }
            else { this.A11yGuideReady(); }
         }
         else if(step == "season")
         {
            scope = this.A11ySeasonScope();
            if(index >= 0 && index < 4 && scope != null && this.A11ySeasonActivate(scope[names[index]] as DisplayObject,true))
            {
               this.mA11yGuidePhase = "entering";
               this.mA11yGuidePhaseAt = getTimer();
               this.mA11yGuideReadyAt = 0;
            }
            else if(index == -1) { this.mA11yGuidePhase = ""; }
            else { this.A11yGuideSeasonDialog(); }
         }
         else if(step == "world")
         {
            if(picked != null) { this.A11yGuideGoToWorld(picked); }
            else { this.mA11yGuidePhase = ""; this.A11yGuideSay("Guide closed. Press Tab to browse the world map."); }
         }
         else if(step == "lots")
         {
            if(picked != null) { this.A11yGuideFurnishDialog(picked); }
            else
            {
               this.mA11yGuidePhase = "entering";
               this.mA11yGuidePhaseAt = getTimer();
               this.mA11yGuideReadyAt = 0;
               CommunicationManager.SendUIMessage("OpenWorldSelection",null);
            }
         }
         else if(step == "furnish")
         {
            if(picked != null) { this.A11yGuideBuy(picked); }
            else { this.A11yGuideLotsDialog(); }
         }
         else if(step == "toodear") { this.A11yGuideFurnishDialog(this.mA11yGuideLot); }
         else if(step == "cantbuy") { this.A11yGuideLotsDialog(); }
         else if(step == "nopanel")
         {
            if(index == 0) { this.A11yGuideLotsDialog(); }
            else { this.mA11yGuidePhase = ""; }
         }
         else if(step == "play")
         {
            if(index == 0) { this.A11yGuidePlay(); }
            else { this.mA11yGuidePhase = ""; }
         }
      }

      // Any guide error closes the guide and says so, so nobody is left waiting.
      public function A11yGuideFailed(e:Error) : void
      {
         this.mA11yGuideState = "done";
         this.mA11yGuidePhase = "";
         this.A11yPostToPython("a11y.mark","guide-error-" + e.message);
         try { this.A11yGuideSay("The guide ran into a problem and closed. You can carry on with the game's own screens."); } catch(e2:Error) { }
      }

      public function A11yGuideFinish() : void
      {
         this.A11yGuideTraitsClose();
         this.mA11yGuideState = "done";
      }
      // END A11Y GUIDED NEW GAME

      // BEGIN A11Y V10 CAS SCOPE
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
         if(this.mA11yBuildCursor || this.mA11yBuildPositionKnown || this.mA11yBuildMarker != null) { this.A11yBuildDisable(true); }
         this.mA11yBuildPositionKnown = false; this.A11yBuildProductForget(); this.mA11yBuildProductModals = 0;
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
         this.mA11yModalReported = ""; this.mA11yBlockingReported = "";
         this.mA11yOwnerReported = "";
         this.mA11yLast = "";
      }

      // END A11Y V10 CAS SCOPE

      public function A11yKeyboardOn(param1:Object = null) : void
      {
         try { this.mA11yKeyboard = true; this.mA11yKeyboardLease = getTimer() + 2000; this.mA11yAutoFocus = true; this.A11yInstallKeyGuards(); this.A11yModalFrame(); }
         catch(e:Error) { }
      }

      public function A11yKeyboardOff(param1:Object = null) : void
      {
         this.mA11yBuildPositionKnown = false; this.A11yBuildProductForget();
         try
         {
            this.A11yKeyProbeOff();
            this.mA11yKeyboard = false;
            this.mA11yAutoFocus = false;
            this.mA11yGuardHeld = new Object();
            this.A11yClearFocus();
            this.mA11yScope = null;
            this.mA11yPendingScope = null;
            this.mA11yActiveModalRoot = null;
            this.mA11yScopeHistory.length = 0;
            this.mA11yHudBrowsing = false;
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
            // Scanner mode setting: in Live the arrows never reach the camera,
            // whoever owns input and even if the keyboard lease lapsed.
            // Text fields keep them. Other keys follow the rules below.
            if(this.mA11yScannerMode && key >= 37 && key <= 40 && !this.mA11yStartupActive && this.A11yWorldHudMode() == 1 && !this.A11yEditing()) { return true; }
            // The Build cursor: arrows, Enter, Space, Backspace, Escape, Page
            // Up/Down, Home, Delete, 1-6 and R are its keys while it owns
            // input; ownership is re-derived at the key, as for the scanner.
            if(this.mA11yBuildGridOn && [8,13,27,32,33,34,36,37,38,39,40,46,49,50,51,52,53,54,82].indexOf(key) >= 0)
            {
               this.A11yModalFrame();
               if(this.A11yBuildGridOwner()) { return true; }
            }
            if([33,34,36,46,49,50,51,52,53,54,82].indexOf(key) >= 0) { return false; }
            if(!this.mA11yKeyboard || getTimer() > this.mA11yKeyboardLease) { return false; }
            if(key == 78) { return !this.A11yEditing() && !this.A11yIsModalScope(this.mA11yScope); }
            if(this.mA11yGuardHeld[key]) { return true; }
            if(this.A11yEditing() && key != 9 && key != 27) { return false; }
            if(this.mA11yStartupActive)
            {
               // Escape belongs to the game unless one of our surfaces owns focus.
               if(key == 27)
               {
                  if(this.mA11yActiveModalRoot != null && this.mA11yActiveModalRoot == this.A11yLauncherNavigation()) { return false; }
                  return this.A11yIsLive(this.mA11yActiveModalRoot) || this.A11yIsModalScope(this.mA11yScope) || this.A11yIsModalScope(this.mA11yPendingScope);
               }
               return true;
            }
            if(this.A11yIsLive(this.mA11yActiveModalRoot)) { return true; }
            if(this.A11yIsModalScope(this.mA11yPendingScope) || this.A11yIsModalScope(this.mA11yScope)) { return true; }
            // Tab enters HUD controls from gameplay, never steals text editing.
            // Scanner mode: Backspace, Enter and Space belong to the scanner
            // while it owns input (the arrows are handled at the top).
            // Escape stays the game's Options menu; Tab and N keep their rules.
            // Ownership is re-derived at the key itself (a pie or dialog may
            // have opened since the last frame), not taken from the cache.
            if(this.mA11yScannerMode && [8,13,32].indexOf(key) >= 0)
            {
               this.A11yModalFrame();
               if(this.A11yScannerOwner()) { return true; }
               // A menu or dialog opened since the last frame owns the key now.
               if(this.A11yIsLive(this.mA11yActiveModalRoot) || this.A11yIsModalScope(this.mA11yScope) || this.A11yIsModalScope(this.mA11yPendingScope)) { return true; }
            }
            return key == 9 && !this.A11yEditing() && this.A11yWorldHudMode() != 0;
         }
         catch(e:Error) { }
         return false;
      }

      public function A11yGuardForBinding(key:int, modifier:int) : Boolean
      {
         // Shift+Tab belongs to EA's first-person camera in the Live world.
         // Only an actual menu/HUD owner borrows it for backward navigation.
         if(key == 9 && modifier == 1 && !this.mA11yStartupActive && this.A11yWorldHudMode() == 1)
         {
            this.A11yModalFrame();
            if(!this.A11yEditing() && !this.mA11yHudBrowsing && !this.A11yIsLive(this.mA11yActiveModalRoot) && !this.A11yIsModalScope(this.mA11yScope) && !this.A11yIsModalScope(this.mA11yPendingScope)) { return false; }
         }
         return this.A11yGuardValid(key);
      }

      public function A11yGuardCheck(key:int, modifier:int = 0) : Function
      {
         var self:TooltipManager = this;
         return function():Boolean { return self.A11yGuardForBinding(key,modifier); };
      }

      public function A11yGuardConsume(key:int, modifier:int = 0) : Function
      {
         var self:TooltipManager = this;
         return function():Boolean
         {
            try
            {
               // A quick Shift+Tab can finish before Python samples Shift.
               // Preserve the modifier attached to EA's actual key binding;
               // navigation still happens once through the existing poller.
               if(self.mA11yStartupActive)
               {
                  self.A11yStartupKey(key,modifier);
                  return false;
               }
               if(key == 9 && !self.mA11yGuardHeld[key])
               {
                  self.mA11yNativeTabDirection = modifier == 1 ? -1 : 1;
                  self.mA11yNativeTabTime = getTimer();
               }
               self.mA11yGuardHeld[key] = true;
            }
            catch(e:Error) { }
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
         var keys:Array = [8,9,13,27,32,37,38,39,40,78,33,34,36,46,49,50,51,52,53,54,82];
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
               while(modifier < (keys[i] == 9 || keys[i] == 82 ? 2 : 1))
               {
                  action = actionClass["WhenTriggered"](triggerClass["FromKeyBinding"](keys[i],keys[i] == 78 ? 3 : modifier));
                  action["SetPriority"](1000000);
                  action["AllowWhileModalOpen"](true);
                  action["SetValidCheck"](this.A11yGuardCheck(keys[i],modifier));
                  action["CallFunction"](this.A11yGuardConsume(keys[i],modifier));
                  if(manager["RegisterAction"](action)) { this.mA11yNativeActions.push(action); }
                  modifier = modifier + 1;
               }
               i = i + 1;
            }
            this.A11yPostToPython("a11y.mark","keyboard-native-guards-" + this.mA11yNativeActions.length);
         }
         catch(e:Error) { this.A11yPostToPython("a11y.mark","keyboard-guard-error"); }
      }

      public function A11yLoadedWidget(name:String) : DisplayObject
      {
         try { if(this.mA11yLayoutManager != null) { return this.mA11yLayoutManager["GetLoadedWidgetByName"](name) as DisplayObject; } }
         catch(e:Error) { }
         return null;
      }

      public function A11yPersistentHud(name:String) : Boolean
      {
         return ["SimInfoTray","SimHub","TimeControls","InteractionQueue","ObjectBoundElements","Notifications","HUDLibrary","UIContainer","SimInfoMotivePanel","SimInfoSkillPanel","SimInfoRelationshipPanel","SimInfoCareerPanel","SimInfoInventoryPanel","SimInfoAspirationPanel","SimInfoSummaryPanel","SimInfoClubPanel","HouseholdInfoVenuePanel"].indexOf(name) >= 0;
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
                  if(this.A11yIsLive(panel) && CommunicationManager.CallUIService("IsWidgetVisibleAndNotHiding",button["PanelName"])) { this.mA11yHudButton = button as DisplayObject; return panel; }
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
            if("btnAdd" in item && "txtLabel" in item) { return true; }
            if(name.indexOf("JobInfoCellView") >= 0 || name.indexOf("PerformanceMoodDetails") >= 0) { return true; }
            if(name.indexOf("ProfileDataCell") >= 0) { return true; }
            if(name.indexOf("BuffIcon") >= 0 || name.indexOf("WhimBubble") >= 0 || name.indexOf("MoodContainer") >= 0) { return true; }
            if(name.indexOf("Calendar.controls::Schedule") >= 0 && name.indexOf("Entry") >= 0) { return true; }
            if(name.indexOf("CommodityContainer") >= 0 || name.indexOf("Moodlet") >= 0 && name.indexOf("Container") < 0) { return true; }
            if(item is TextField)
            {
               return item.parent != null && getQualifiedClassName(item.parent).indexOf("SchedulePane") >= 0 && TextField(item).text.length > 0;
            }
            if("TooltipExt" in item && Object(item)["TooltipExt"]["Text"] != null && String(Object(item)["TooltipExt"]["Text"]).length > 0) { return true; }
         }
         catch(e:Error) { }
         return false;
      }

      public function A11yTabControl(direction:int) : void
      {
         if(this.mA11yBuildCursor || this.mA11yBuildMarker != null) { this.A11yBuildDisable(); this.A11yBuildReply(0,"off"); }
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
            // A fast Shift+Tab can leave a pending Tab bit after Shift is
            // released. The native camera change owns that press; it must
            // not also enter the HUD through the Python keyboard poller.
            if(getTimer() < this.mA11yFirstPersonFence) { return; }
            if(this.mA11yPendingScope != null || this.mA11yIdxDir != 0) { this.mA11yNavQueue.push(direction * 3); return; }
            if(this.mA11yScope == null)
            {
               this.mA11yScope = this.mTooltipsLayer.stage;
               this.mA11yHudBrowsing = true;
            }
            // Simplified menus have one option sequence, not separate Tab
            // groups and spatial arrow columns. The logical list walker also
            // reveals offscreen/recycled rows and reaches confirm/cancel.
            if(this.mA11ySimplifiedMenus && this.A11ySimplifiedActive()) { this.A11yTabMove(direction); return; }
            list = this.A11yFindScrollList(this.mA11yFocused);
            if(list != null) { this.mA11yListMemory[list] = this.mA11yLogicalIndex; }
            current = this.A11yGroupOwner(this.mA11yFocused);
            if(current != null) { this.mA11yGroupMemory[current] = this.mA11yFocused; }
            if(!this.A11yCollectBuildSections(all))
            {
               this.A11yCollectFocusables(this.mA11yScope != null ? this.mA11yScope : this.mTooltipsLayer.stage,all,0);
               all.sort(this.A11ySortFocusables);
            }
            while(i < all.length)
            {
               list = this.A11yFindScrollList(all[i]);
               owner = this.A11yGroupOwner(all[i]);
               if(owners.indexOf(owner) < 0) { owners.push(owner); groups.push(all[i]); }
               i = i + 1;
            }
            if(groups.length == 0) { return; }
            // One group only (a dialog whose answers share a list): walk its
            // controls by plain focus. The list-index path selects picker cells,
            // which activates a CAS story answer without Enter (seen 2026-09-16).
            if(groups.length == 1 && all.length > 1) { if(!this.A11yGroupArrow(direction)) { this.A11yTabMove(direction); } return; }
            index = owners.indexOf(current);
            index = index < 0 ? (direction > 0 ? 0 : groups.length - 1) : (index + direction + groups.length) % groups.length;
            target = groups[index];
            owner = owners[index];
            if(this.A11yIsLive(this.mA11yGroupMemory[owner])) { target = this.mA11yGroupMemory[owner]; }
            list = this.A11yFindScrollList(target);
            if(list != null)
            {
               i = this.mA11yListMemory[list] != undefined ? int(this.mA11yListMemory[list]) : 0;
               if(DisplayObject(list).name.toLowerCase().indexOf("filter") >= 0 || getQualifiedClassName(owner).indexOf("Filter") >= 0)
               {
                  var filterCell:DisplayObject = null;
                  for each(filterCell in this.A11yGridLayout(list)["GetAllDisplayObjectCells"]())
                  {
                     if("Selected" in filterCell && Object(filterCell)["Selected"]) { i = this.A11yCellIndexOf(this.A11yGridLayout(list),filterCell); break; }
                  }
               }
               i = Math.max(0,Math.min(i,int(this.A11yGridLayout(list)["GetNumItems"]()) - 1));
               if(this.A11yRequestIndex(list,i,direction)) { return; }
            }
            this.A11yFocusItem(target);
         }
         catch(e:Error) { }
      }

      // Build mode Tab (RimWorld Access style): the catalog sections in the
      // order players need them, filters, search, the Build/Buy/Function tabs,
      // categories, then the products and their swatches. EA's tool buttons
      // (BuildBuyInspector: undo, sledgehammer and so on) have native hotkeys
      // and are left out. Only while browsing the Build panels from the world;
      // menus, dialogs and Live mode keep the full screen order.
      public function A11yBuildSections() : Array
      {
         var roots:Array = new Array();
         var nav:Object = null;
         var catalog:Object = null;
         var filter:DisplayObject = null;
         try
         {
            if(this.A11yWorldHudMode() != 2 || !this.mA11yHudBrowsing || this.A11yIsLive(this.mA11yActiveModalRoot)) { return roots; }
            filter = this.A11yLoadedWidget("BuildBuyFilter");
            if(this.A11yIsLive(filter)) { roots.push(filter); }
            nav = this.A11yLoadedWidget("BuildBuyNavigation");
            if(nav != null)
            {
               if(this.A11yIsLive(nav["mcSearchContainer"])) { roots.push(nav["mcSearchContainer"]); }
               if(this.A11yIsLive(nav["mcButtonContainer"])) { roots.push(nav["mcButtonContainer"]); }
               if(this.A11yIsLive(nav["mcNavPanel"])) { roots.push(nav["mcNavPanel"]); }
            }
            catalog = this.A11yLoadedWidget("BuildBuyProductCatalog");
            if(catalog != null && catalog["mcCatalog"] != null)
            {
               if(this.A11yIsLive(catalog["mcCatalog"]["mcCatalog"])) { roots.push(catalog["mcCatalog"]["mcCatalog"]); }
               if(this.A11yIsLive(catalog["mcCatalog"]["mcVariationSelector"])) { roots.push(catalog["mcCatalog"]["mcVariationSelector"]); }
            }
         }
         catch(e:Error) { }
         return roots;
      }

      public function A11yCollectBuildSections(all:Array) : Boolean
      {
         var roots:Array = this.A11yBuildSections();
         var part:Array = null;
         var i:int = 0;
         var j:int = 0;
         try
         {
            while(i < roots.length)
            {
               part = new Array();
               this.A11yCollectFocusables(roots[i],part,0);
               part.sort(this.A11ySortFocusables);
               j = 0;
               while(j < part.length)
               {
                  if(all.indexOf(part[j]) < 0) { all.push(part[j]); }
                  j = j + 1;
               }
               i = i + 1;
            }
         }
         catch(e:Error) { }
         return all.length > 0;
      }

      public function A11yMsgTabNext(param1:Object = null) : void
      {
         if(this.A11yReturnToCatalog()) { return; }
         try { this.A11yTabControl(this.A11yNativeTab(1)); } catch(e:Error) { }
      }

      public function A11yMsgTabPrev(param1:Object = null) : void
      {
         if(this.A11yReturnToCatalog()) { return; }
         try { this.A11yTabControl(this.A11yNativeTab(-1)); } catch(e:Error) { }
      }

      public function A11yNativeTab(fallback:int) : int
      {
         var direction:int = this.mA11yNativeTabDirection;
         this.mA11yNativeTabDirection = 0;
         if(direction != 0 && getTimer() - this.mA11yNativeTabTime < 1000) { return direction; }
         return fallback;
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
               if("mScrollerView" in node && "mSlider" in node) { view = node["mScrollerView"] as DisplayObjectContainer; slider = node["mSlider"]; }
               if("mcView" in node && "mcSlider" in node) { view = node["mcView"] as DisplayObjectContainer; slider = node["mcSlider"]; }
               if("mcScheduleView" in node && "mcScheduleSlider" in node) { view = node["mcScheduleView"] as DisplayObjectContainer; slider = node["mcScheduleSlider"]; }
               if("mcSaveListView" in node && "mcSaveListSlider" in node) { view = node["mcSaveListView"] as DisplayObjectContainer; slider = node["mcSaveListSlider"]; }
               if(view != null && slider != null && "mcMask" in view)
               {
                  bounds = item.getBounds(view);
                  viewport = Object(view)["mcMask"].getBounds(view);
                  offset = bounds.top < viewport.top ? bounds.top - viewport.top : (bounds.bottom > viewport.bottom ? bounds.bottom - viewport.bottom : 0);
                  if(offset != 0) { slider["SetCurrentValue"](Number(slider["Value"]) + offset,false,true,true); }
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
               if("A11yAnnounceMood" in this.mA11yFocused) { Object(this.mA11yFocused)["A11yAnnounceMood"](); }
               else
               {
                  this.A11yAnnounceDisplay(this.mA11yFocused,"a11y.focus_enc",true);
                  // Re-arm the selected row's native tooltip after the final
                  // label, preserving its delayed description and custom UI.
                  this.A11yFocusHover(null,this.mA11yFocused);
                  if(getQualifiedClassName(this.mA11yFocused).indexOf("CalendarDayView") >= 0)
                  {
                     Object(this.mA11yFocused)["TooltipExt"]["Show"](true);
                  }
                  else
                  {
                     var hover:DisplayObject = this.A11yHoverProxy(this.mA11yFocused);
                     if(hover != null && "GetExtension" in hover)
                     {
                        var tooltipClass:Object = getDefinitionByName("olympus.extensions.TooltipExtension");
                        var extension:Object = tooltipClass["Get"](hover,false);
                        if(extension != null && (extension["Text"] != null || extension["Data"] != null)) { extension["Show"](true); }
                     }
                  }
               }
            }
            this.mA11yFocusPending = null;
         }
         catch(e:Error) { this.mA11yFocusPending = null; }
      }

      public function A11yReadCurrent(param1:Object = null) : void
      {
         try
         {
            if(this.mA11yFocused != null)
            {
               this.mA11yLast = "";
               this.A11yFocusHover(null,this.mA11yFocused);
               if("A11yAnnounceMood" in this.mA11yFocused) { Object(this.mA11yFocused)["A11yAnnounceMood"](); }
               else { this.A11yAnnounceDisplay(this.mA11yFocused,"a11y.focus_enc",true); }
            }
         }
         catch(e:Error) { }
      }

      public function A11yReturnRow(param1:Object = null) : void
      {
         try
         {
            if(this.mA11yReturnList != null && this.A11yIsLive(this.mA11yReturnList as DisplayObject) && this.mA11yReturnIndex >= 0)
            {
               this.A11yRequestIndex(this.mA11yReturnList,this.mA11yReturnIndex,-1);
            }
         }
         catch(e:Error) { }
      }

      public function A11yMsgToggle(param1:Object = null) : void
      {
         try { this.A11yActivate(false); } catch(e:Error) { }
      }

      public function A11yPickerFooter(item:DisplayObject, advance:Boolean = false) : Boolean
      {
         var owner:Object = item;
         var button:DisplayObject = null;
         try
         {
            while(owner != null && owner != this.mTooltipsLayer.stage)
            {
               if(advance && "mcNextButton" in owner) { button = owner["mcNextButton"] as DisplayObject; }
               else if(!advance && "btnDone" in owner) { button = owner["btnDone"] as DisplayObject; }
               if(button != null && this.A11yIsLive(button))
               {
                  this.A11yFocusItem(button);
                  if(advance && Object(button)["enabled"]) { this.A11yActivate(false); }
                  return true;
               }
               owner = owner.parent;
            }
         }
         catch(e:Error) { }
         return false;
      }

      public function A11yCalendarStep(direction:int, vertical:Boolean) : Boolean
      {
         try
         {
            if(this.mA11yFocused == null || getQualifiedClassName(this.mA11yFocused).indexOf("CalendarDayView") < 0) { return false; }
            this.A11yIndexScroll(direction * (vertical ? 7 : 1),false);
            // Calendar edges stop; Tab leaves the date grid for the schedule.
            return true;
         }
         catch(e:Error) { }
         return false;
      }

      public function A11yCalendarLabel(item:DisplayObject) : String
      {
         var calendar:Object = this.A11yLoadedWidget("Calendar");
         var list:Object = null;
         var index:int = -1;
         try
         {
            if(calendar == null || getQualifiedClassName(item).indexOf("CalendarDayView") < 0) { return ""; }
            list = calendar["mcCalendarDays"];
            index = this.A11yCellIndexOf(this.A11yGridLayout(list),item);
            if(index >= 0)
            {
               var data:Object = this.A11yGridLayout(list)["GetDataFeed"]()["RequestItemAt"](index);
               var offset:int = data is int ? int(data) : int(data["mCurrentDayOffset"]);
               return TextField(calendar["txtWeekday" + int(index % 7)]).text + ". " + (offset == 0 ? "Today" : (offset == 1 ? "Tomorrow" : (offset > 0 ? offset + " days from today" : -offset + " days ago")));
            }
         }
         catch(e:Error) { }
         return "";
      }

      public function A11yCalendarSchedule() : void
      {
         var calendar:Object = this.A11yLoadedWidget("Calendar");
         var items:Array = new Array();
         try
         {
            if(calendar == null) { return; }
            this.A11yCollectFocusables(calendar["mcSchedulePane"],items,0);
            items.sort(this.A11ySortFocusables);
            if(items.length > 0) { this.A11yFocusItem(items[0]); }
         }
         catch(e:Error) { }
      }

      public function A11yClock(param1:Object = null) : void
      {
         var clock:Object = this.A11yLoadedWidget("TimeControls");
         var text:String = "";
         try
         {
            if(this.A11yIsLive(clock as DisplayObject))
            {
               text = clock["txtGameTime"]["text"];
               if(text != null && text.length > 0 && clock["txtTimeSpeedName"]["visible"] && clock["txtTimeSpeedName"]["text"].length > 0)
               {
                  text = text + ". " + clock["txtTimeSpeedName"]["text"];
               }
            }
         }
         catch(e:Error) { }
         if(text == null) { text = ""; }
         // Dedicated response, including missing-widget feedback; hovering
         // the clock cannot masquerade as a keyboard request completing.
         var payload:String = encodeURIComponent("clock:" + text);
         payload = payload.split("'").join("%27");
         payload = payload.split("(").join("%28");
         payload = payload.split(")").join("%29");
         payload = payload.split("!").join("%21");
         this.A11yPostToPython("a11y.clock_enc",payload);
      }

      public function A11yMood(param1:Object = null) : void
      {
         var hub:Object = this.A11yLoadedWidget("SimHub");
         try
         {
            if(!this.mA11yKeyboard || this.mA11yActiveModalRoot != null) { return; }
            // The whole panel is read in one reply by SimHub's MoodContainer,
            // the only movie defining it and the buff classes it reads; it is
            // reached by name so no other movie resolves those classes.
            if(this.A11yIsLive(hub as DisplayObject) && hub["mcMoodContainer"] != null)
            {
               hub["mcMoodContainer"]["A11yReadMood"]();
               return;
            }
         }
         catch(e:Error) { }
         // Not live (Build Mode, main menu): an empty reply is spoken as unavailable.
         this.A11yPostToPython("a11y.mood_enc","");
      }

      // Enter on an item of the Sim's inventory opens the TS4 Access item
      // menu (Python, a11y.invitem_enc) instead of EA's pie menu; its Item
      // actions row sends A11yInvItemActions to replay the original click.
      // Multiselect keeps EA's click (it toggles a selection). By name only:
      // the inventory classes exist only in SimInfoInventoryPanel.
      public function A11yInventoryMenu(item:DisplayObject) : Boolean
      {
         var panel:DisplayObject = null;
         var id:String = null;
         try
         {
            if(item == null || getQualifiedClassName(item).indexOf("InventoryCellViewButton") < 0) { return false; }
            panel = this.A11yLoadedWidget("SimInfoInventoryPanel");
            if(panel == null || !this.A11yIsInside(item,panel)) { return false; }
            if(Object(panel)["btnMultiselect"] == null || Object(panel)["btnMultiselect"]["Selected"] != false) { return false; }
            id = String(Object(item)["GetObjectId"]());
            if(id == null || id.length == 0 || id == "0" || id == "null" || id == "undefined") { return false; }
            this.mA11yInvCell = item;
            this.A11yPostToPython("a11y.invitem_enc",encodeURIComponent(id));
            return true;
         }
         catch(e:Error) { }
         return false;
      }

      public function A11yInvItemActions(param1:Object = null) : void
      {
         var cell:DisplayObject = this.mA11yInvCell;
         this.mA11yInvCell = null;
         try
         {
            if(cell == null || cell.stage == null || !this.A11yIsLive(cell)) { return; }
            this.mA11yActivating = true;
            this.A11ySafeDispatch(cell,MouseEvent.MOUSE_DOWN);
            this.A11ySafeDispatch(cell,MouseEvent.MOUSE_UP);
            this.A11ySafeDispatch(cell,MouseEvent.CLICK);
            this.mA11yActivating = false;
         }
         catch(e:Error) { this.mA11yActivating = false; }
      }

      public function A11yWants(param1:Object = null) : void
      {
         var hub:Object = this.A11yLoadedWidget("SimHub");
         try
         {
            if(!this.mA11yKeyboard || !this.A11yIsLive(hub as DisplayObject) || this.mA11yActiveModalRoot != null) { return; }
            this.mA11yStatusScope = hub["mcWhimPanel"] as DisplayObject;
            this.A11yFocusInto(this.mA11yStatusScope);
         }
         catch(e:Error) { }
      }

      public function A11yNeeds(param1:Object = null) : void
      {
         try
         {
            if(this.mA11yKeyboard && this.mA11yActiveModalRoot == null) { CommunicationManager.SendUIMessage("OpenSimInfoMotivePanel",{"bStayOpen":true}); }
         }
         catch(e:Error) { }
      }

      public function A11yPhoneFrame() : void
      {
         var state:Object = null;
         var tray:Object = null;
         var button:DisplayObject = null;
         try
         {
            if(this.mA11yPhoneOwner.length == 0) { return; }
            if(!this.mA11yKeyboard || getTimer() > this.mA11yPhoneUntil) { this.mA11yPhoneOwner = ""; return; }
            state = getDefinitionByName("gamedata.Gameplay.shared.GameplayStateData");
            if(String(state["ActiveSimId"]) != this.mA11yPhoneOwner) { return; }
            tray = this.A11yLoadedWidget("SimInfoTray");
            if(tray == null) { return; }
            if(this.A11yIsLive(tray["mcPhoneAlert"])) { this.mA11yPhoneOwner = ""; this.A11yFocusInto(tray["mcPhoneAlert"]); return; }
            // Wait for the native call notification to finish switching Sims.
            if(!this.A11yIsLive(tray["mcIncomingPhone"])) { return; }
            button = tray["btnPhone"];
            if(!this.A11yIsLive(button)) { return; }
            this.mA11yPhoneOwner = "";
            this.mA11yActivating = true;
            this.A11ySafeDispatch(button,MouseEvent.MOUSE_DOWN);
            this.A11ySafeDispatch(button,MouseEvent.MOUSE_UP);
            this.A11ySafeDispatch(button,MouseEvent.CLICK);
            this.mA11yActivating = false;
         }
         catch(e:Error) { this.mA11yActivating = false; this.mA11yPhoneOwner = ""; }
      }

      public function TooltipManager(param1:Layer, param2:ITooltip)
      {
         super();
         this.mTooltips = new Object();
         this.mTooltipsLayer = param1;
         this.mDefaultTooltip = param2;
         sInstance = this;
         this.A11yInstallGameMessageHook();
         this.A11yTryHookStage();
         if(this.mTooltipsLayer != null)
         {
            this.mTooltipsLayer.addEventListener(Event.ADDED_TO_STAGE,this.A11yOnLayerStaged,false,0,true);
            this.mTooltipsLayer.addEventListener(Event.REMOVED_FROM_STAGE,this.A11yOnLayerRemoved,false,0,true);
         }
      }

      public static var sA11yPick:Object = null;

      public static var sA11yTravelLease:int = 0;
      public static var sA11yTravelLeaseTime:int = 0;
      public static var sA11yTravelList:Boolean = false;

      public static function A11yTravelCanRoute() : Boolean
      {
         var now:int = getTimer();
         return sInstance != null && sInstance.mA11yKeyboard && now <= sInstance.mA11yKeyboardLease && sA11yTravelList && sA11yTravelLease > 0 && now >= sA11yTravelLeaseTime && now - sA11yTravelLeaseTime <= 5000;
      }

      public static var sA11yHooked:Boolean = false;

      public function A11yInstallGameMessageHook() : void
      {
         try
         {
            if(!ExternalInterface.available)
            {
               return;
            }
            ExternalInterface.addCallback("SendMessage",this.A11yOnGameMessage);
            sA11yHooked = true;
         }
         catch(e:Error)
         {
            sA11yHooked = false;
         }
      }

      public function A11yMsgHook(param1:Object = null) : void
      {
         var wasStartup:Boolean = this.mA11yStartupActive;
         this.mA11yZoneSeen = true;
         this.mA11yStartupActive = false;
         this.mA11yStartupKeys.length = 0;
         this.mA11yGuardHeld = new Object();
         this.mA11yModalReported = ""; this.mA11yBlockingReported = "";
         this.A11yInstallGameMessageHook();
         // Leaving startup mode here must be reported like the frame path
         // does, or Python keeps swallowing the key poller for the whole
         // lot (2026-09-16 "keys dead in the lot, no -native mark").
         // The flag is already false, so this goes through the native
         // command path, which is live once A11yHook arrives.
         if(wasStartup) { this.A11yPostToPython("a11y.mark","startup-v11-native"); }
      }

      public function A11yOnGameMessage(param1:String, param2:Object = null) : Boolean
      {
         try
         {
            // Diagnostic only: prove the native M entry reaches this callback
            // before introducing any alternate routing. Forward it unchanged.
            if(param1 == "GoToNeigborhoodTravel") { this.A11yPostToPython("a11y.mark","travel-native-message-v14b"); }
            if(param1 != null && param1.length > 4 && param1.substr(0,4) == "A11y") { this.mA11yZoneSeen = true; }
            if(param1 != null && param1.length > 5 && param1.substr(0,5) == "A11y|")
            {
               this.A11yHandleEncoded(param1);
               return true;
            }
         }
         catch(e:Error)
         {
         }
         return CommunicationManager.SendUIMessage(param1,param2);
      }

      // TS4 Access Plus catalog bridge (from the TS4 Access Plus 0.7 add-on,
      // which patched it into gamedata.shared.ResourceKey in every movie).
      // "A11y|plus|ping" answers pong; "A11y|plus|catalog|type|tags|serial"
      // lists a Build/Buy category through EA's BBRequestProductCatalog, in
      // pages of 25 "name~price~colors" items; "A11y|plus|select|index"
      // chooses one of them exactly as a catalog click does (the same
      // CatalogProduct.Select call the Build cursor's product restore uses).
      // Replies go to a11yplus.flash; EA's BBNotifyError text is forwarded as
      // "builderror|text" so the build helper can say why a step failed.
      public function A11yPlusHandle(parts:Array) : void
      {
         var cmd:String = String(parts[2]);
         try
         {
            if(!this.mA11yPlusListening)
            {
               this.mA11yPlusListening = true;
               CommunicationManager.AddMessageListenerByName("BBNotifyError",this.A11yPlusError,"A11yPlus");
            }
            if(cmd == "ping") { this.A11yPlusReply("pong"); }
            else if(cmd == "catalog" && parts.length >= 6) { this.A11yPlusCatalog(int(parts[3]),String(parts[4]),String(parts[5])); }
            else if(cmd == "select" && parts.length >= 4) { this.A11yPlusSelect(int(parts[3])); }
            else if(cmd == "browse" && parts.length >= 8) { this.A11yCatalogBrowse(int(parts[3]),String(parts[4]),String(parts[5]),String(parts[6]),decodeURIComponent(String(parts[7]))); }
         }
         catch(e:Error) { this.A11yPlusReply("error|" + e.message); }
      }

      public function A11yPlusError(data:Object) : void
      {
         var cls:Class = null;
         var key:Object = null;
         try
         {
            cls = getDefinitionByName("olympus.localization.LocKey") as Class;
            key = new cls("hash" in data ? data : data["labelKey"]);
            this.A11yPlusReply("builderror|" + encodeURIComponent(String(key.toString())));
         }
         catch(e:Error) { }
      }

      public function A11yPlusReply(text:String) : void
      {
         this.A11yPostToPython("a11yplus.flash",encodeURIComponent(text));
      }

      public function A11yPlusCatalog(productType:int, tagNames:String, serial:String) : void
      {
         var filterClass:Class = getDefinitionByName("gamedata.BuildBuy.shared.ProductFilter") as Class;
         var productClass:Class = getDefinitionByName("gamedata.BuildBuy.shared.CatalogProduct") as Class;
         var categories:Object = getDefinitionByName("gamedata.BuildBuy.constants.FilterCategories");
         var tagUtils:Object = getDefinitionByName("olympus.utils.TuningTagsUtils");
         var filter:Object = new filterClass();
         var tags:Array = new Array();
         var names:Array = tagNames.split(",");
         var index:int = 0;
         var start:int = 0;
         var raw:Array = null;
         var items:Array = new Array();
         var product:Object = null;
         while(index < names.length)
         {
            if(names[index] != "" && categories[names[index]] != undefined) { tags.push(tagUtils["GetTagValueFromHash"](categories[names[index]])); }
            index = index + 1;
         }
         filter["productType"] = productType;
         filter["categoryTags"] = tags;
         raw = CommunicationManager.CallGameService("BBRequestProductCatalog",filter["ToObject"]()) as Array;
         this.mA11yPlusProducts = new Array();
         if(raw != null)
         {
            index = 0;
            while(index < raw.length)
            {
               product = new productClass(raw[index]);
               this.mA11yPlusProducts.push(product);
               items.push(encodeURIComponent(String(product["Name"])) + "~" + String(product["price"]) + "~" + String(product["variationCount"]));
               index = index + 1;
            }
         }
         while(start < items.length)
         {
            this.A11yPlusReply("cat|" + serial + "|" + start + "|" + items.length + "|" + items.slice(start,start + 25).join("^"));
            start = start + 25;
         }
         this.A11yPlusReply("catend|" + serial + "|" + items.length);
      }

      public function A11yPlusSelect(index:int) : void
      {
         var product:Object = null;
         if(index < 0 || index >= this.mA11yPlusProducts.length)
         {
            this.A11yPlusReply("error|no such product");
            return;
         }
         product = this.mA11yPlusProducts[index];
         product["Select"](null,null,0,2,int(product["stateIndex"]));
         this.A11yPlusReply("selected|" + index + "|" + encodeURIComponent(String(product["Name"])));
      }

      // Catalog tree (tyjokr_a11y_catalog.py): one Buy panel button's filter, or
      // a search. Tag names resolve as FilterButton.CategoryTags does: a
      // FilterCategories group (Array) expands with TuningTagsUtils.GetGroup, a
      // single hash with GetTagValueFromHash. A search is the Buy panel's open
      // search (BuildBuyNavigationMain.OnSearch): searchResult.devString, sorted
      // by SEARCHGROUP_OPENSEARCH_SORT. Replies and selection are A11yPlusCatalog's.
      public function A11yCatalogTags(names:String) : Array
      {
         var categories:Object = getDefinitionByName("gamedata.BuildBuy.constants.FilterCategories");
         var tagUtils:Object = getDefinitionByName("olympus.utils.TuningTagsUtils");
         var list:Array = names.split(",");
         var tags:Array = new Array();
         var value:Object = null;
         var group:Array = null;
         var index:int = 0;
         var inner:int = 0;
         while(index < list.length)
         {
            value = list[index] != "" ? categories[list[index]] : null;
            if(value != null && value is Array)
            {
               group = tagUtils["GetGroup"](value) as Array;
               inner = 0;
               while(group != null && inner < group.length) { tags.push(group[inner]); inner = inner + 1; }
            }
            else if(value != null)
            {
               value = tagUtils["GetTagValueFromHash"](value);
               if(value != null) { tags.push(value); }
            }
            index = index + 1;
         }
         return tags;
      }

      public function A11yCatalogBrowse(productType:int, tagNames:String, priorityNames:String, serial:String, search:String) : void
      {
         var filterClass:Class = getDefinitionByName("gamedata.BuildBuy.shared.ProductFilter") as Class;
         var productClass:Class = getDefinitionByName("gamedata.BuildBuy.shared.CatalogProduct") as Class;
         var filter:Object = new filterClass();
         var resultClass:Class = null;
         var raw:Array = null;
         var items:Array = new Array();
         var product:Object = null;
         var index:int = 0;
         var start:int = 0;
         filter["productType"] = productType;
         if(search != "")
         {
            resultClass = getDefinitionByName("gamedata.BuildBuy.shared.SearchResult") as Class;
            filter["searchResult"] = new resultClass();
            filter["searchResult"]["devString"] = search;
            filter["categoryPriorityTags"] = this.A11yCatalogTags("SEARCHGROUP_OPENSEARCH_SORT");
         }
         else
         {
            filter["categoryTags"] = this.A11yCatalogTags(tagNames);
            filter["categoryPriorityTags"] = this.A11yCatalogTags(priorityNames);
         }
         raw = CommunicationManager.CallGameService("BBRequestProductCatalog",filter["ToObject"]()) as Array;
         this.mA11yPlusProducts = new Array();
         while(raw != null && index < raw.length)
         {
            product = new productClass(raw[index]);
            this.mA11yPlusProducts.push(product);
            items.push(encodeURIComponent(String(product["Name"])) + "~" + String(product["price"]) + "~" + String(product["variationCount"]));
            index = index + 1;
         }
         while(start < items.length)
         {
            this.A11yPlusReply("cat|" + serial + "|" + start + "|" + items.length + "|" + items.slice(start,start + 25).join("^"));
            start = start + 25;
         }
         this.A11yPlusReply("catend|" + serial + "|" + items.length);
      }

      public function A11yHandleEncoded(param1:String) : void
      {
         var _loc2_:Array = param1.split("|");
         if(_loc2_[1] == "lotprice" && _loc2_.length == 4)
         {
            this.A11yLotRentalPrice(String(_loc2_[2]),String(_loc2_[3]));
            return;
         }
         if(_loc2_[1] == "travelready" && _loc2_.length == 3)
         {
            sA11yTravelLease = int(_loc2_[2]);
            sA11yTravelLeaseTime = getTimer();
            CommunicationManager.SendUIMessage("A11yTravelReady",{"epoch":sA11yTravelLease});
            return;
         }
         if(_loc2_[1] == "travellist" && _loc2_.length == 3)
         {
            sA11yTravelList = _loc2_[2] == "on";
            return;
         }
         if(_loc2_[1] == "simplifiedmenus" && _loc2_.length == 3)
         {
            if(_loc2_[2] == "on" || _loc2_[2] == "off") { this.A11ySetSimplifiedMenus(_loc2_[2] == "on"); }
            return;
         }
         if(_loc2_[1] == "travelresult" && _loc2_.length >= 5)
         {
            CommunicationManager.SendUIMessage("A11yTravelResult",{"epoch":int(_loc2_[2]),"request":int(_loc2_[3]),"outcome":String(_loc2_[4]),"reason":_loc2_.length > 5 ? String(_loc2_[5]) : ""});
            return;
         }
         if(_loc2_[1] == "buildcontrols" && _loc2_.length == 3)
         {
            if(_loc2_[2] == "on" || _loc2_[2] == "off") { this.A11yBuildSetControls(_loc2_[2] == "on"); }
            return;
         }
         if(_loc2_[1] == "scannermode" && _loc2_.length == 3)
         {
            if(_loc2_[2] == "on" || _loc2_[2] == "off")
            {
               this.mA11yScannerMode = _loc2_[2] == "on";
               // Re-post the owner and Live states on the next frame: the
               // mode heartbeat also heals a lost post.
               this.mA11yScannerOwnerReported = "";
               this.mA11yScannerLiveReported = "";
            }
            return;
         }
         if(_loc2_[1] == "buildhand" && _loc2_.length == 4 && _loc2_[2] == "drop") { this.A11yBuildHandDrop(String(_loc2_[3])); return; }
         if(_loc2_[1] == "buildaim" && _loc2_.length == 8) { this.A11yBuildAim(_loc2_); return; }
         if(_loc2_[1] == "build" && _loc2_.length == 4) { this.A11yBuildCommand(String(_loc2_[2]),int(_loc2_[3])); return; }
         if(_loc2_[1] == "plus" && _loc2_.length >= 3) { this.A11yPlusHandle(_loc2_); return; }
         if(_loc2_[1] == "keyup") { delete this.mA11yGuardHeld[int(_loc2_[2])]; return; }
         if(_loc2_[1] == "lease") { this.mA11yKeyboardLease = getTimer() + 2000; return; }
         if(_loc2_[1] == "phone") { this.mA11yPhoneOwner = String(_loc2_[2]); this.mA11yPhoneUntil = getTimer() + 4000; return; }
         var _loc3_:String = _loc2_.length > 1 ? String(_loc2_[1]) : "";
         if(_loc3_ == "loc" && _loc2_.length > 3)
         {
            this.A11yResolveLoc(String(_loc2_[2]),String(_loc2_[3]));
         }
         else if(_loc3_ == "cap")
         {
            this.A11yShowCaption(decodeURIComponent(param1.substr(9)));
         }
         else if(_loc3_ == "pick" && _loc2_.length > 9)
         {
            sA11yPick = {
               "objectId":String(_loc2_[2]),
               "pickType":int(_loc2_[3]),
               "lotId":uint(_loc2_[4]),
               "simFirstName":String(_loc2_[5]),
               "x":Number(_loc2_[6]),
               "y":Number(_loc2_[7]),
               "z":Number(_loc2_[8]),
               "level":int(_loc2_[9])
            };
            CommunicationManager.SendUIMessage("A11yOpenPieMenu",sA11yPick);
         }
      }

      public function A11yLotRentalPrice(zone:String, generation:String) : void
      {
         // Keep 64-bit zone IDs as strings through the native service boundary.
         if(!/^[0-9]{1,20}$/.test(zone) || !/^[0-9]{1,20}$/.test(generation)) { return; }
         var price:Number = 0;
         try
         {
            var raw:Object = CommunicationManager.CallGameService("GetNeighborhoodLotData",zone);
            var calculator:Object = CommunicationManager.CallGameService("GetLotRentalPriceCalculator");
            if(raw != null && calculator != null)
            {
               // Mirrors NeighborhoodLotData's LotPrice/HousePrice/TotalPrice
               // and VacationRentalPrice getters. FULLY_CONTAINED_PLEX == 1.
               var plex:Boolean = Number(raw.buildingType) == 1;
               var land:Number = plex ? Number(raw.depositBase) : (raw.lotDescriptionData != null ? Number(raw.lotDescriptionData.price) : NaN);
               var house:Number = plex ? 0 : Number(raw.housePrice);
               var furniture:Number = Number(raw.furnishingsPrice);
               var multiply:Number = Number(calculator.multiply);
               var add:Number = Number(calculator.add);
               var total:Number = land + house + furniture;
               var calculated:Number = total * multiply + add;
               // Missing data must fall back to native travel, never wrap an
               // invalid or negative value into an enormous uint charge.
               if(isFinite(land) && isFinite(house) && isFinite(furniture) &&
                  land >= 0 && house >= 0 && furniture >= 0 &&
                  isFinite(multiply) && multiply >= 0 && isFinite(add) && total > 0 &&
                  isFinite(calculated) && calculated >= 1 && calculated <= 4294967295)
               {
                  price = uint(calculated);
               }
            }
         }
         catch(e:Error) { price = 0; }
         this.A11yPostToPython("a11y.lotprice_enc",zone + "|" + String(price) + "|" + generation);
      }

      public function A11yResolveLoc(param1:String, param2:String) : void
      {
         var _loc3_:String = "";
         var _loc4_:Class = null;
         var _loc5_:Object = null;
         try
         {
            _loc4_ = getDefinitionByName("olympus.localization.LocKey") as Class;
            _loc5_ = _loc4_["FromHash"](uint(param2));
            _loc3_ = String(_loc5_.toString());
         }
         catch(e:Error)
         {
            _loc3_ = "";
         }
         try
         {
            this.A11yPostToPython("a11y.loc_enc",param1 + "|" + encodeURIComponent(_loc3_));
         }
         catch(e:Error)
         {
         }
      }

      public function A11yMsgHidePieMenu(param1:Object = null) : void
      {
         try
         {
            CommunicationManager.SendMessage("HidePieMenu",null);
         }
         catch(e:Error)
         {
         }
      }

      public function A11yOnLayerStaged(param1:Event) : void
      {
         if(param1.target != this.mTooltipsLayer)
         {
            return;
         }
         this.A11yTryHookStage();
         this.A11yLayoutCaption();
      }

      public function A11yOnLayerRemoved(param1:Event) : void
      {
         if(param1.target != this.mTooltipsLayer) { return; }
         // A departing movie may stop receiving frames before its mode guard runs.
         if(this.mA11yBuildCursor || this.mA11yBuildPositionKnown || this.mA11yBuildMarker != null) { this.A11yBuildDisable(true); }
         this.mA11yBuildPositionKnown = false; this.A11yBuildProductForget(); this.mA11yBuildProductModals = 0;
      }

      public function A11yShowCaption(param1:String) : void
      {
         var _loc2_:TextFormat = null;
         try
         {
            if(param1 == null || param1.length == 0)
            {
               this.A11yHideCaption();
               return;
            }
            // Allocate once per manager, then reuse across announcements.
            if(this.mA11yCaption == null)
            {
               this.mA11yCaption = new Sprite();
               this.mA11yCaption.name = "A11yCaption";
               this.mA11yCaption.mouseEnabled = false;
               this.mA11yCaption.mouseChildren = false;
               this.mA11yCaptionText = new TextField();
               this.mA11yCaptionText.mouseEnabled = false;
               this.mA11yCaptionText.selectable = false;
               this.mA11yCaptionText.multiline = true;
               this.mA11yCaptionText.wordWrap = true;
               this.mA11yCaptionText.embedFonts = true;
               _loc2_ = new TextFormat("$TextFont",22,16777215);
               _loc2_.align = "center";
               this.mA11yCaptionText.defaultTextFormat = _loc2_;
               this.mA11yCaptionText.x = 16;
               this.mA11yCaptionText.y = 10;
               this.mA11yCaption.addChild(this.mA11yCaptionText);
            }
            this.mA11yCaptionText.text = param1;
            this.mA11yCaption.visible = true;
            this.mA11yCaptionUntil = getTimer() + 8000;
            this.A11yLayoutCaption();
            this.mA11yCaption.addEventListener(Event.ENTER_FRAME,this.A11yCaptionFrame,false,0,true);
         }
         catch(e:Error)
         {
         }
      }

      public function A11yHideCaption() : void
      {
         try
         {
            if(this.mA11yCaption != null)
            {
               this.mA11yCaption.visible = false;
               this.mA11yCaption.removeEventListener(Event.ENTER_FRAME,this.A11yCaptionFrame);
            }
         }
         catch(e:Error)
         {
         }
      }

      public function A11yCaptionFrame(param1:Event) : void
      {
         try
         {
            if(getTimer() >= this.mA11yCaptionUntil)
            {
               this.A11yHideCaption();
            }
         }
         catch(e:Error)
         {
         }
      }

      public function A11yLayoutCaption() : void
      {
         var _loc1_:Stage = null;
         var _loc2_:Point = null;
         var _loc3_:Point = null;
         var _loc4_:Number = 0;
         var _loc5_:Number = 0;
         try
         {
            if(this.mA11yCaption == null || this.mTooltipsLayer == null)
            {
               return;
            }
            _loc1_ = this.mTooltipsLayer.stage;
            if(_loc1_ == null)
            {
               return;
            }
            _loc1_.addEventListener(Event.RESIZE,this.A11yCaptionResize,false,0,true);
            _loc2_ = this.mTooltipsLayer.globalToLocal(new Point(0,0));
            _loc3_ = this.mTooltipsLayer.globalToLocal(new Point(_loc1_.stageWidth,_loc1_.stageHeight));
            _loc4_ = Math.max(80,Math.min(760,_loc3_.x - _loc2_.x - 40));
            this.mA11yCaptionText.width = _loc4_ - 32;
            this.mA11yCaptionText.height = this.mA11yCaptionText.textHeight + 8;
            _loc5_ = this.mA11yCaptionText.height + 20;
            this.mA11yCaption.graphics.clear();
            this.mA11yCaption.graphics.beginFill(0,0.8);
            this.mA11yCaption.graphics.drawRoundRect(0,0,_loc4_,_loc5_,12,12);
            this.mA11yCaption.graphics.endFill();
            this.mA11yCaption.x = _loc2_.x + (_loc3_.x - _loc2_.x - _loc4_) / 2;
            this.mA11yCaption.y = Math.max(_loc2_.y + 20,_loc3_.y - _loc5_ - 40);
            this.mTooltipsLayer.addChild(this.mA11yCaption);
         }
         catch(e:Error)
         {
         }
      }

      public function A11yCaptionResize(param1:Event) : void
      {
         try
         {
            this.A11yLayoutCaption();
         }
         catch(e:Error)
         {
         }
      }

      public function A11yOnTooltipFrame(param1:Event) : void
      {
         var _loc2_:DisplayObject = null;
         try
         {
            _loc2_ = param1.target as DisplayObject;
            if(_loc2_ == null)
            {
               return;
            }
            _loc2_.removeEventListener(Event.ENTER_FRAME,this.A11yOnTooltipFrame);
            this.A11yAnnounceDisplay(_loc2_,"a11y.speak_enc");
         }
         catch(e:Error)
         {
         }
      }

      public function A11yTryHookStage() : void
      {
         var _loc1_:Stage = null;
         try
         {
            if(this.mA11yStageHooked)
            {
               return;
            }
            if(this.mTooltipsLayer == null)
            {
               return;
            }
            _loc1_ = this.mTooltipsLayer.stage;
            if(_loc1_ == null)
            {
               return;
            }
            var delegateClass:Object = getDefinitionByName("scaleform.clik.managers.InputDelegate");
            var inputEventClass:Object = getDefinitionByName("scaleform.clik.events.InputEvent");
            delegateClass["getInstance"]()["addEventListener"](inputEventClass["INPUT"],this.A11yKeyboardSuppress,false,1000000,true);
            _loc1_.addEventListener(MouseEvent.MOUSE_OVER,this.A11yOnMouseOver,true,0,true);
            _loc1_.addEventListener(MouseEvent.MOUSE_DOWN,this.A11yOnStageClick,true,0,true);
            // One input path only. A screen that starts forwarding Flash
            // key events must not also activate via capture, bubble and polling.
            try
            {
               if(_loc1_.focus == null)
               {
                  _loc1_.focus = _loc1_;
               }
            }
            catch(focusErr:Error)
            {
            }
            this.mA11yStageHooked = true;
            this.A11yStartupInstall();
            CommunicationManager.AddMessageListenerByName("A11yKeyboardOn",this.A11yKeyboardOn,"A11yNarrator");
            CommunicationManager.AddMessageListenerByName("A11yKeyboardOff",this.A11yKeyboardOff,"A11yNarrator");
            CommunicationManager.AddMessageListenerByName("A11yKeyProbeOn",this.A11yKeyProbeOn,"A11yNarrator");
            CommunicationManager.AddMessageListenerByName("A11yKeyProbeOff",this.A11yKeyProbeOff,"A11yNarrator");
            CommunicationManager.AddMessageListenerByName("A11yTabNext",this.A11yMsgTabNext,"A11yNarrator");
            CommunicationManager.AddMessageListenerByName("A11yTabPrev",this.A11yMsgTabPrev,"A11yNarrator");
            CommunicationManager.AddMessageListenerByName("A11yReadCurrent",this.A11yReadCurrent,"A11yNarrator");
            CommunicationManager.AddMessageListenerByName("A11yInspect",this.A11yInspect,"A11yNarrator");
            CommunicationManager.AddMessageListenerByName("A11yClock",this.A11yClock,"A11yNarrator");
            CommunicationManager.AddMessageListenerByName("A11yMood",this.A11yMood,"A11yNarrator");
            CommunicationManager.AddMessageListenerByName("A11yInvItemActions",this.A11yInvItemActions,"A11yNarrator");
            CommunicationManager.AddMessageListenerByName("A11yBuildGridOn",this.A11yBuildGridOnMsg,"A11yNarrator");
            CommunicationManager.AddMessageListenerByName("A11yBuildGridOff",this.A11yBuildGridOffMsg,"A11yNarrator");
            CommunicationManager.AddMessageListenerByName("A11yWants",this.A11yWants,"A11yNarrator");
            CommunicationManager.AddMessageListenerByName("A11yNeeds",this.A11yNeeds,"A11yNarrator");
            CommunicationManager.AddMessageListenerByName("A11yToggle",this.A11yMsgToggle,"A11yNarrator");
            CommunicationManager.AddMessageListenerByName("A11yReturnRow",this.A11yReturnRow,"A11yNarrator");
            this.mTooltipsLayer.addEventListener(Event.ENTER_FRAME,this.A11yModalFrame,false,0,true);
            CommunicationManager.AddMessageListenerByName("A11yReadDialog",this.A11yReadDialog,"A11yNarrator");
            CommunicationManager.AddMessageListenerByName("A11yDismiss",this.A11yDismiss,"A11yNarrator");
            CommunicationManager.AddMessageListenerByName("A11yEscape",this.A11yEscape,"A11yNarrator");
            CommunicationManager.AddMessageListenerByName("A11yNavNext",this.A11yMsgNext,"A11yNarrator");
            CommunicationManager.AddMessageListenerByName("A11yNavPrev",this.A11yMsgPrev,"A11yNarrator");
            CommunicationManager.AddMessageListenerByName("A11yActivate",this.A11yMsgActivate,"A11yNarrator");
            CommunicationManager.AddMessageListenerByName("A11yClearFocus",this.A11yMsgClear,"A11yNarrator");
            CommunicationManager.AddMessageListenerByName("A11yAutoFocusOn",this.A11yMsgAutoFocusOn,"A11yNarrator");
            CommunicationManager.AddMessageListenerByName("A11yAutoFocusOff",this.A11yMsgAutoFocusOff,"A11yNarrator");
            CommunicationManager.AddMessageListenerByName("A11yArrowUp",this.A11yMsgArrowUp,"A11yNarrator");
            CommunicationManager.AddMessageListenerByName("A11yArrowDown",this.A11yMsgArrowDown,"A11yNarrator");
            CommunicationManager.AddMessageListenerByName("A11yArrowLeft",this.A11yMsgArrowLeft,"A11yNarrator");
            CommunicationManager.AddMessageListenerByName("A11yArrowRight",this.A11yMsgArrowRight,"A11yNarrator");
            CommunicationManager.AddMessageListenerByName("A11yHook",this.A11yMsgHook,"A11yNarrator");
            CommunicationManager.AddMessageListenerByName("A11yHidePieMenu",this.A11yMsgHidePieMenu,"A11yNarrator");
         }
         catch(e:Error)
         {
         }
      }

      public function A11yModalFrame(param1:Event = null) : void
      {
         var request:Object = null;
         var dialog:DisplayObject = null;
         var previous:Object = null;
         var active:Boolean = false;
         var editing:Boolean = false;
         var state:String = null;
         var top:DisplayObject = null;
         // Guided New Game: offer the guide once a new family's CAS is ready.
         this.A11yGuideFrame();
         try
         {
            var hudMode:int = this.A11yWorldHudMode();
            if(hudMode != this.mA11yHudMode)
            {
               this.mA11yCatalogReleased = null;
               this.mA11yBuildGridOn = false;
               if(this.mA11yHudBrowsing)
               {
                  this.A11yClearFocus();
                  this.mA11yHudBrowsing = false;
                  this.mA11yScope = null;
                  this.mA11yScopeHistory.length = 0;
               }
               this.mA11yHudMode = hudMode;
            }
            if(this.mA11yDialogManager == null)
            {
               try { this.mA11yDialogManager = getDefinitionByName("olympus.dialog.DialogManager"); }
               catch(loadError:Error) { }
            }
            if(this.mA11yDialogManager != null && this.mA11yDialogManager["IsInstantiated"]())
            {
               request = this.mA11yDialogManager["GetCurrentRequest"]();
               dialog = request != null ? request["dialog"] as DisplayObject : null;
            }
            this.mA11yManagedDialog = dialog;
            this.mA11yModalWidget = this.A11yTopModalWidget();
            this.mA11yHudRoot = this.A11yOpenHud();
            top = this.mA11yModalWidget;
            if(top == null) { top = this.mA11yHudRoot; }
            var pie:DisplayObject = this.A11yLoadedWidget("PieMenu");
            if(this.A11yIsLive(pie) && "mcMenu" in pie && this.A11yIsLive(Object(pie)["mcMenu"]) && (top == null || this.A11yIsAbove(pie,top))) { top = pie; }
            if(dialog != null && this.A11yIsLive(dialog) && (top == null || this.A11yIsAbove(dialog,top)))
            {
               top = dialog;
            }
            // HolidaySettings is an overlay that is not always registered
            // in the modal stack; use its actual visible content and z-order.
            var holiday:DisplayObject = this.A11yLoadedWidget("HolidaySettings");
            if(this.A11yIsLive(holiday) && "mcContent" in holiday && this.A11yIsLive(Object(holiday)["mcContent"]) && CommunicationManager.CallUIService("IsWidgetVisibleAndNotHiding","HolidaySettings") && (top == null || this.A11yIsAbove(holiday,top))) { top = holiday; }
            var season:DisplayObject = this.A11ySeasonScope();
            if(season != null && (top == null || this.A11yIsAbove(season,top) || this.A11yIsInside(season,top))) { top = season; }
            var story:DisplayObject = this.A11yCASStoryScope();
            if(story != null && (top == null || this.A11yIsAbove(story,top))) { top = story; }
            if(top == null && this.mA11yStartupActive && hudMode == 0) { top = this.A11yLauncherNavigation(); }
            var filter:DisplayObject = this.A11yFilterPopup(top);
            if(filter != null) { top = filter; }
            var dropdown:DisplayObject = this.A11yCurrentDropdown();
            if(dropdown != this.mA11yDropdown)
            {
               if(dropdown != null)
               {
                  this.mA11yDropdownExtension = this.A11yFindDropdownExtension(this.mA11yFocused,dropdown);
                  this.mA11yDropdownButton = this.mA11yDropdownExtension != null ? this.mA11yDropdownExtension["btnDropdown"] as DisplayObject : this.mA11yFocused;
               }
               else { this.mA11yResumeFocus = this.mA11yDropdownButton; }
               this.mA11yDropdown = dropdown;
            }
            if(dropdown != null) { top = dropdown; }
            if(this.mA11yCatalogReleased != null)
            {
               if(!this.A11yIsLive(this.mA11yCatalogReleased)) { this.mA11yCatalogReleased = null; }
               else if(top != null && (top == this.mA11yCatalogReleased || this.A11yIsBuildBuy(top))) { top = null; }
            }
            if((this.mA11yBuildCursor || this.mA11yBuildMarker != null) && !this.A11yBuildBlocked()) { top = null; }
            if(this.mA11yKeyboard && top != this.mA11yActiveModalRoot)
            {
               this.mA11yActiveModalRoot = top;
               if(top != null)
               {
                  this.mA11yHudBrowsing = false;
                  if(!this.A11yIsInside(this.mA11yStatusScope,top)) { this.mA11yStatusScope = null; }
                  this.A11yFocusHover(this.mA11yFocused,null);
                  this.A11yFocusInto(top);
                  // The marketplace interstitial at the main menu is closed for keyboard
                  // users (user decision 2026-09-16); speech-only users keep it.
                  if(this.mA11yStartupActive && this.mA11yKeyboard && getQualifiedClassName(top).indexOf("FSInterstitialMessageDialog") >= 0) { this.mA11yInterstitialAt = getTimer() + 600; }
               }
               else if(this.mA11yStatusScope == null && !this.mA11yHudBrowsing)
               {
                  // Cached PieMenu/Picker roots can remain visible after
                  // their contents close. Loaded is not the same as open.
                  this.A11yClearFocus();
                  this.mA11yScope = null;
                  this.mA11yScopeHistory.length = 0;
               }
            }
            if(this.mA11yScope != null && !this.A11yIsModalScope(this.mA11yScope) && this.mA11yPendingScope == null)
            {
               this.A11yCancelIndex();
               this.mA11yScope = null;
               this.mA11yFocused = null;
               this.mA11yList = null;
               this.A11yClearRing();
               while(this.mA11yScopeHistory.length > 0)
               {
                  previous = this.mA11yScopeHistory.pop();
                  if(this.A11yIsModalScope(previous.scope))
                  {
                     this.mA11yScope = previous.scope;
                     if(this.A11yIsLive(previous.focus)) { this.A11yFocusItem(previous.focus); }
                     break;
                  }
               }
            }
            active = this.mA11yKeyboard && (this.A11yIsLive(this.mA11yActiveModalRoot) || this.A11yIsModalScope(this.mA11yScope) || this.A11yIsModalScope(this.mA11yPendingScope));
            this.A11yFocusSettled();
            if(active && this.A11yIsLive(this.mA11yFocused)) { this.A11yDrawFocusRing(this.mA11yFocused); }
            this.A11yBuildFrame();
            this.A11yPhoneFrame();
            if(this.mTooltipsLayer != null && this.mTooltipsLayer.stage != null)
            {
               editing = this.mTooltipsLayer.stage.focus is TextField && TextField(this.mTooltipsLayer.stage.focus).type == "input";
            }
            this.A11yFollowCASInput();
            state = (active ? "1" : "0") + (editing ? "1" : "0");
            // Navigation ownership includes HUD panels; only blocking surfaces
            // must prevent a phone request from switching its recipient Sim.
            var blockingState:String = this.A11yPhoneBlocking(top) ? "1" : "0";
            var context:String = (top != null ? getQualifiedClassName(top) + "/" + top.name : "world") + ":" + state + blockingState;
            if(context != this.mA11yOwnerReported)
            {
               this.mA11yOwnerReported = context;
               this.A11yPostToPython("a11y.context_enc",encodeURIComponent(context));
            }
            if(state != this.mA11yModalReported)
            {
               this.mA11yModalReported = state;
               this.A11yPostToPython("a11y.modalstate",state);
            }
            if(blockingState != this.mA11yBlockingReported)
            {
               this.mA11yBlockingReported = blockingState;
               this.A11yPostToPython("a11y.blocking",blockingState);
            }
            var buildGridState:String = this.A11yBuildGridOwner() ? "1" : "0";
            if(buildGridState != this.mA11yBuildGridReported)
            {
               this.mA11yBuildGridReported = buildGridState;
               this.A11yPostToPython("a11y.buildgridowner",buildGridState);
            }
            var scannerState:String = this.A11yScannerOwner() ? "1" : "0";
            if(scannerState != this.mA11yScannerOwnerReported)
            {
               this.mA11yScannerOwnerReported = scannerState;
               this.A11yPostToPython("a11y.scannerowner",scannerState);
            }
            // Live camera eligibility for the scanner mode camera follow:
            // Live mode with the setting on, whatever owns the keys.
            var firstPerson:Boolean = this.A11yFirstPersonState();
            var scannerLive:String = this.mA11yScannerMode && !this.mA11yStartupActive && this.A11yWorldHudMode() == 1 && !firstPerson ? "1" : "0";
            if(scannerLive != this.mA11yScannerLiveReported)
            {
               this.mA11yScannerLiveReported = scannerLive;
               this.A11yPostToPython("a11y.scannerlive",scannerLive);
            }
         }
         catch(e:Error) { }
      }

      public function A11yPhoneBlocking(top:DisplayObject) : Boolean
      {
         // A real dialog remains blocking even if a HUD panel is above it.
         return this.A11yIsLive(this.mA11yManagedDialog) || this.A11yIsLive(this.mA11yModalWidget) || (top != null && top != this.mA11yHudRoot);
      }

      public function A11yIsModalScope(scope:DisplayObject) : Boolean
      {
         var name:String = null;
         try
         {
            if(scope == null || !this.mA11yKeyboard || !this.A11yIsLive(scope)) { return false; }
            if(this.mA11yHudBrowsing && scope == this.mTooltipsLayer.stage) { return true; }
            if(scope == this.mA11yStatusScope) { return true; }
            if(this.mA11yActiveModalRoot is DisplayObjectContainer && DisplayObjectContainer(this.mA11yActiveModalRoot).contains(scope)) { return true; }
            return scope == this.mA11yActiveModalRoot;
         }
         catch(e:Error) { }
         return false;
      }

      public function A11yScannerOwner() : Boolean
      {
         try
         {
            if(!this.mA11yScannerMode || !this.mA11yKeyboard || getTimer() > this.mA11yKeyboardLease) { return false; }
            if(this.mA11yStartupActive || this.A11yWorldHudMode() != 1 || this.A11yEditing()) { return false; }
            if(this.mA11yBuildCursor || this.mA11yHudBrowsing || this.mA11yStatusScope != null) { return false; }
            if(this.A11yIsLive(this.mA11yActiveModalRoot)) { return false; }
            if(this.A11yIsModalScope(this.mA11yScope) || this.A11yIsModalScope(this.mA11yPendingScope)) { return false; }
            return true;
         }
         catch(e:Error) { }
         return false;
      }

      public function A11yWorldHudMode() : int
      {
         if(this.A11yIsLive(this.A11yLoadedWidget("SimInfoTray"))) { return 1; }
         if(this.A11yIsLive(this.A11yLoadedWidget("BuildBuyNavigation"))) { return 2; }
         return 0;
      }

      public function A11yTopModalWidget() : DisplayObject
      {
         var node:DisplayObject = this.mTooltipsLayer;
         var api:Object = null;
         var names:Array = null;
         var candidate:DisplayObject = null;
         var best:DisplayObject = null;
         var i:int = 0;
         try
         {
            if(this.mA11yLayoutManager == null)
            {
               while(node != null)
               {
                  if("layoutMgr" in node) { this.mA11yLayoutManager = Object(node)["layoutMgr"]; break; }
                  node = node.parent;
               }
               if(this.mA11yLayoutManager == null)
               {
                  api = getDefinitionByName("olympus.gamepad.LayoutAPI");
                  this.mA11yLayoutManager = api["mLayoutMgr"];
               }
            }
            if(this.mA11yLayoutManager == null) { return null; }
            names = this.mA11yLayoutManager["GetCurrentModalWidgetsNames"]();
            i = 0;
            while(i < names.length)
            {
               if(!this.A11yPersistentHud(String(names[i])) && CommunicationManager.CallUIService("IsWidgetTopModal",names[i]))
               {
                  candidate = this.mA11yLayoutManager["GetLoadedWidgetByName"](names[i]) as DisplayObject;
                  if(this.A11yIsLive(candidate) && CommunicationManager.CallUIService("IsWidgetVisibleAndNotHiding",names[i]) && (best == null || this.A11yIsAbove(candidate,best))) { best = candidate; }
               }
               i = i + 1;
            }
         }
         catch(e:Error) { }
         return best;
      }

      public function A11yIsAbove(first:DisplayObject, second:DisplayObject) : Boolean
      {
         var a:Array = new Array();
         var b:Array = new Array();
         var node:DisplayObject = null;
         var common:DisplayObjectContainer = null;
         try
         {
            if(first == second) { return true; }
            node = first;
            while(node != null) { a.unshift(node); node = node.parent; }
            node = second;
            while(node != null) { b.unshift(node); node = node.parent; }
            while(a.length > 0 && b.length > 0 && a[0] == b[0])
            {
               common = a.shift() as DisplayObjectContainer;
               b.shift();
            }
            if(a.length == 0) { return false; }
            if(b.length == 0) { return true; }
            if(common != null) { return common.getChildIndex(a[0]) > common.getChildIndex(b[0]); }
         }
         catch(e:Error) { }
         return false;
      }

      public function A11yReadDialog(param1:Object = null) : void
      {
         var target:DisplayObject = null;
         try
         {
            target = this.mA11yPendingScope != null ? this.mA11yPendingScope : this.mA11yScope;
            if(target != null)
            {
               this.mA11yLast = "";
               this.A11yAnnounceDisplay(target,"a11y.widget_enc",true);
            }
         }
         catch(e:Error) { }
      }

      public function A11yEscape(param1:Object = null) : void
      {
         // Polling may see Options open before it sees the Escape press
         // that opened it. Only dismiss for a physical press claimed by
         // our native guard; scanner/numpad Back has its own message.
         if(this.mA11yGuardHeld[27]) { this.A11yDismiss(); }
      }

      public function A11yDismiss(param1:Object = null) : void
      {
         var owner:Object = null;
         try
         {
            if(this.mA11yActiveModalRoot == this.mA11yManagedDialog && this.mA11yManagedDialog != null && this.mA11yDialogManager != null)
            {
               this.mA11yDialogManager["HandleEscapeKey"]();
               return;
            }
            owner = this.mA11yPendingScope != null ? this.mA11yPendingScope : this.mA11yScope;
            if(owner != null && owner.parent != null && "SetFilterPanelVisible" in owner.parent && "mcFilterPanel" in owner.parent && Object(owner.parent)["mcFilterPanel"] == owner)
            {
               this.mA11yResumeFocus = owner.parent["mcFilterBubble"];
               owner.parent["SetFilterPanelVisible"](false);
               return;
            }
            if(this.mA11yDropdown != null)
            {
               if(this.mA11yDropdownExtension != null) { this.mA11yDropdownExtension["Close"](); }
               return;
            }
            if(this.A11yReleaseBuildCatalog()) { return; }
            if(owner == this.mA11yStatusScope)
            {
               this.mA11yStatusScope = null;
               this.A11yClearFocus();
               this.mA11yScope = null;
               return;
            }
            if(owner == this.mTooltipsLayer.stage && this.mA11yHudBrowsing)
            {
               this.mA11yHudBrowsing = false;
               this.A11yClearFocus();
               this.mA11yScope = null;
               return;
            }
            if(owner != null && getQualifiedClassName(owner).indexOf("PieMenu") >= 0)
            {
               if("mcMenu" in owner) { owner["mcMenu"]["GoBack"](); }
               return;
            }
            if(owner == this.mA11yHudRoot && this.mA11yHudButton != null)
            {
               if(getQualifiedClassName(owner).indexOf("PhoneAlert") >= 0 && "HideAlert" in owner) { owner["HideAlert"](); return; }
               // Closing through the opener must not hover/announce it.
               this.A11yClickControl(this.mA11yHudButton);
               return;
            }
            while(owner != null)
            {
               if("A11yDismissPanel" in owner) { owner["A11yDismissPanel"](); return; }
               if("HandleRequestHide" in owner) { owner["HandleRequestHide"](null); return; }
               if("WidgetName" in owner) { CommunicationManager.CallUIService("RequestHide" + owner["WidgetName"],null); return; }
               owner = owner.parent;
            }
         }
         catch(e:Error) { }
      }

      public function A11yCancelIndex() : void
      {
         try
         {
            if(this.mTooltipsLayer != null)
            {
               this.mTooltipsLayer.removeEventListener(Event.ENTER_FRAME,this.A11yIndexFrame);
               this.mTooltipsLayer.removeEventListener(Event.ENTER_FRAME,this.A11yScrollFrame);
            }
            this.mA11yIdxDir = 0;
            this.mA11yScrollDir = 0;
            this.mA11yIdxList = null;
            this.mA11yIdxLayout = null;
            this.mA11yNavQueue.length = 0;
            this.mA11yLogicalList = null;
            this.mA11yLogicalIndex = -1;
         }
         catch(e:Error) { }
      }

      public function A11yDrainNav() : void
      {
         var direction:int = 0;
         try
         {
            while(this.mA11yIdxDir == 0 && this.mA11yPendingScope == null && this.mA11yNavQueue.length > 0)
            {
               direction = int(this.mA11yNavQueue.shift());
               if(direction == 0) { this.A11yActivate(); }
               else if(direction == 4) { this.A11yActivate(false); }
               else if(direction == 3 || direction == -3) { this.A11yTabControl(int(direction / 3)); }
               else if(direction == 2 || direction == -2) { this.A11yArrowHorizontal(int(direction / 2)); }
               else if(direction == 5 || direction == -5) { this.A11yArrowNav(int(direction / 5)); }
               else { this.A11yTabMove(direction); }
            }
         }
         catch(e:Error) { }
      }

      public function A11yFindWidget(param1:DisplayObject) : DisplayObject
      {
         var current:DisplayObject = param1;
         var depth:int = 0;
         try
         {
            while(current != null && depth < 26)
            {
               if(this.A11yIsFocusable(current)) { return current; }
               current = current.parent;
               depth = depth + 1;
            }
         }
         catch(e:Error) { }
         return null;
      }


      public function A11yGroupText(param1:DisplayObject) : DisplayObject
      {
         var _loc2_:DisplayObject = null;
         var _loc3_:DisplayObject = null;
         var _loc4_:int = 0;
         var _loc5_:Number = 0;
         var _loc6_:Number = 0;
         var _loc7_:Rectangle = null;
         try
         {
            _loc3_ = param1;
            if(param1.stage == null)
            {
               return param1;
            }
            _loc5_ = param1.stage.stageWidth * 0.45;
            _loc6_ = param1.stage.stageHeight * 0.45;
            _loc2_ = param1.parent;
            while(_loc2_ != null && _loc4_ < 6)
            {
               if(this.mTooltipsLayer != null && _loc2_ == this.mTooltipsLayer)
               {
                  break;
               }
               _loc7_ = _loc2_.getBounds(_loc2_.stage);
               if(_loc7_.width > _loc5_ || _loc7_.height > _loc6_)
               {
                  break;
               }
               _loc3_ = _loc2_;
               _loc2_ = _loc2_.parent;
               _loc4_++;
            }
         }
         catch(e:Error)
         {
         }
         return _loc3_;
      }

      // CAS paints the collapsed name separately from its transparent button.
      // Use the visible label as the semantic target; retain EA click behavior.
      public function A11yCASNameLabel(item:DisplayObject) : DisplayObject
      {
         var owner:Object = null;
         var label:DisplayObject = null;
         var button:DisplayObject = null;
         try
         {
            if(item == null || item.parent == null) { return null; }
            owner = item.parent;
            if(getQualifiedClassName(owner) != "widgets.CAS.NameField::CASNameFieldMain") { return null; }
            label = owner["txtFullNameDisplay"] as DisplayObject;
            button = owner["btnTextEffect"] as DisplayObject;
            if(item != label && item != button) { return null; }
            if(!this.A11yIsLive(label) || button == null || button.parent != owner || !button.visible) { return null; }
            if("enabled" in button && Object(button)["enabled"] == false) { return null; }
            if("mouseEnabled" in button && Object(button)["mouseEnabled"] == false) { return null; }
            return label;
         }
         catch(e:Error) { }
         return null;
      }

      public function A11yActivateCASName(item:DisplayObject) : Boolean
      {
         var button:DisplayObject = null;
         try
         {
            if(item == null || this.A11yCASNameLabel(item) != item) { return false; }
            button = Object(item.parent)["btnTextEffect"] as DisplayObject;
            this.mA11yActivating = true;
            this.A11ySafeDispatch(button,MouseEvent.MOUSE_DOWN);
            this.A11ySafeDispatch(button,MouseEvent.MOUSE_UP);
            this.A11ySafeDispatch(button,MouseEvent.CLICK);
            this.mA11yActivating = false;
            this.mA11yList = null;
            return true;
         }
         catch(e:Error) { this.mA11yActivating = false; }
         return false;
      }

      // Observe native CAS editing without stealing its TextField focus/caret.
      public function A11yCASInputField(focus:DisplayObject) : DisplayObject
      {
         var owner:DisplayObject = focus;
         var controls:Object = null;
         var field:DisplayObject = null;
         var depth:int = 0;
         try
         {
            while(owner != null && depth < 10)
            {
               if(getQualifiedClassName(owner) == "widgets.CAS.NameField::CASNameFieldMain")
               {
                  controls = Object(owner)["mcEditModeControls"];
                  if(controls == null) { return null; }
                  field = controls["txtFirstName"] as DisplayObject;
                  if(this.A11yIsLive(field) && this.A11yIsInside(focus,field)) { return field; }
                  field = controls["txtLastName"] as DisplayObject;
                  if(this.A11yIsLive(field) && this.A11yIsInside(focus,field)) { return field; }
                  return null;
               }
               owner = owner.parent;
               depth = depth + 1;
            }
         }
         catch(e:Error) { }
         return null;
      }

      public function A11yFollowCASInput() : void
      {
         var input:TextField = null;
         var field:DisplayObject = null;
         var label:String = "";
         var value:String = "";
         var previous:DisplayObject = this.mA11yCASInput;
         var owner:Object = null;
         try
         {
            if(this.mA11yKeyboard && this.mTooltipsLayer != null && this.mTooltipsLayer.stage != null)
            {
               input = this.mTooltipsLayer.stage.focus as TextField;
               if(input != null && input.type == "input") { field = this.A11yCASInputField(input); }
            }
            if(field == this.mA11yCASInput) { return; }
            this.mA11yCASInput = field;
            if(field == null)
            {
               if(previous != null && this.mA11yFocused == previous)
               {
                  this.A11yClearRing();
                  this.mA11yFocused = null;
                  this.mA11yFocusPending = null;
                  this.mA11yList = null;
                  owner = previous.parent != null ? previous.parent.parent : null;
                  if(owner != null && getQualifiedClassName(owner) == "widgets.CAS.NameField::CASNameFieldMain" && "txtFullNameDisplay" in owner)
                  {
                     this.mA11yFocused = this.A11yCASNameLabel(owner["txtFullNameDisplay"] as DisplayObject);
                  }
                  this.mA11yLastWidget = this.mA11yFocused;
               }
               return;
            }
            this.mA11yFocused = field;
            this.mA11yLastWidget = field;
            this.mA11yFocusPending = null;
            this.mA11yList = null;
            this.A11yDrawFocusRing(field);
            // DefaultText is setter-only in EA's EditTextField. Its public
            // txtDefault retains the localized label even while hidden.
            if("txtDefault" in field && Object(field)["txtDefault"] != null) { label = this.A11yTextValue(Object(field)["txtDefault"] as TextField); }
            value = this.A11yTextValue(input);
            if(label.length == 0) { this.A11yAnnounceDisplay(field,"a11y.focus_enc",false); return; }
            if(value.length > 0 && value != label) { label = label + ". " + value; }
            this.A11yPostToPython("a11y.focus_enc",encodeURIComponent("0|0|" + label));
         }
         catch(e:Error) { this.mA11yCASInput = null; }
      }


      public function A11yIsFocusable(param1:DisplayObject) : Boolean
      {
         var name:String = null;
         var sprite:Sprite = null;
         try
         {
            if(this.mA11ySimplifiedMenus && this.A11ySaveChoice(param1)) { return true; }
            if(this.A11yCASNameLabel(param1) == param1 && param1 != null) { return true; }
            if(param1 is TextField) { return TextField(param1).type == "input"; }
            if("txtInput" in param1 && "txtStatic" in param1) { return true; }
            if(param1 is SimpleButton || param1 is Button) { return true; }
            name = getQualifiedClassName(param1);
            // DialogButton/Footer are layout wrappers. Their visible inner
            // Button owns the mouse handler. Never stop at a wrapper name.
            if(name.indexOf("widgets.Dialog.") == 0) { return false; }
            if(name == "widgets.CAS.Stories::ButtonSelectionGrid") { return false; }
            if(name.indexOf("Button") >= 0 || name.indexOf("Checkbox") >= 0 || name.indexOf("CellView") >= 0) { return true; }
            sprite = param1 as Sprite;
            return sprite != null && sprite.buttonMode;
         }
         catch(e:Error) { }
         return false;
      }


      public function A11yCollectFocusables(param1:DisplayObject, param2:Array, param3:int) : void
      {
         var _loc4_:DisplayObjectContainer = null;
         var _loc5_:int = 0;
         var _loc6_:Rectangle = null;
         var _loc7_:String = null;
         if(param1 == null || param2.length > 4096 || param3 > 40)
         {
            return;
         }
         if(!param1.visible || param1.alpha <= 0.01)
         {
            return;
         }
         if(this.mTooltipsLayer != null && param1 == this.mTooltipsLayer)
         {
            return;
         }
         _loc7_ = getQualifiedClassName(param1);
         if(_loc7_ == "widgets.GameEntry.WorldSelection.SeasonSelect::SeasonSelectContainer")
         {
            var seasons:Array = ["btnSpring","btnSummer","btnFall","btnWinter"];
            var seasonIndex:int = 0;
            while(seasonIndex < seasons.length)
            {
               var seasonName:String = seasons[seasonIndex];
               var seasonButton:DisplayObject = Object(param1)[seasonName] as DisplayObject;
               if(this.A11yIsLive(seasonButton)) { param2.push(seasonButton); }
               seasonIndex++;
            }
            return;
         }
         if(this.A11yKeyboardDecoration(param1)) { return; }
         if(this.A11ySemanticTarget(param1) != param1) { return; }
         if("A11yMotiveText" in param1 || "btnSolve" in param1)
         {
            param2.push(param1);
            return;
         }
         if(_loc7_.indexOf("PieMenu") >= 0 && _loc7_.indexOf("PieMenuButton") < 0)
         {
            _loc4_ = param1 as DisplayObjectContainer;
            if(_loc4_ != null)
            {
               _loc5_ = 0;
               while(_loc5_ < _loc4_.numChildren)
               {
                  this.A11yCollectFocusables(_loc4_.getChildAt(_loc5_),param2,param3 + 1);
                  _loc5_++;
               }
               return;
            }
         }
         // Business employee cells (BusinessEmployeeManagement, used by
         // retail stores and the WickedWhims strip club): a Sim to hire is
         // the cell itself; a current employee's cell is disabled but holds
         // Promote, Demote and Fire. Keep the cell and those buttons
         // reachable (2026-10-04, Leo could only hire with the mouse).
         if("btnFire" in param1 && "btnPromote" in param1 && "btnDemote" in param1 && "mcSatisfactionTooltipHolder" in param1)
         {
            _loc6_ = param1.getBounds(param1.stage);
            if(_loc6_.width > 2 && _loc6_.height > 2 && (this.A11yIntersectsStage(param1) || this.A11yCanRevealOnStage(param1)) && this.A11yInListViewport(param1)) { param2.push(param1); }
            this.A11yCollectFocusables(Object(param1)["btnPromote"] as DisplayObject,param2,param3 + 1);
            this.A11yCollectFocusables(Object(param1)["btnDemote"] as DisplayObject,param2,param3 + 1);
            this.A11yCollectFocusables(Object(param1)["btnFire"] as DisplayObject,param2,param3 + 1);
            return;
         }
         if(!this.A11yCompositeRow(param1) && (this.A11yIsFocusable(param1) || this.A11yInformational(param1)))
         {
            _loc6_ = param1.getBounds(param1.stage);
            if(_loc6_.width > 2 && _loc6_.height > 2 && (this.A11yIntersectsStage(param1) || this.A11yCanRevealOnStage(param1)) && this.A11yInListViewport(param1))
            {
               param2.push(param1);
            }
            // Informational rows can contain actions (calendar edit/delete,
            // profile controls). Keep both the row and its children reachable.
            if(this.A11yInformational(param1) && !this.A11yIsFocusable(param1) && this.A11yActionProxy(param1) == param1)
            {
               _loc4_ = param1 as DisplayObjectContainer;
               if(_loc4_ != null)
               {
                  _loc5_ = 0;
                  while(_loc5_ < _loc4_.numChildren) { this.A11yCollectFocusables(_loc4_.getChildAt(_loc5_),param2,param3 + 1); _loc5_ = _loc5_ + 1; }
               }
            }
            // Trait slots expose a separate Remove action on hover.
            // Keep it reachable without treating decorative button artwork
            // as additional controls.
            if("btnRemove" in param1)
            {
               this.A11yCollectFocusables(Object(param1)["btnRemove"] as DisplayObject,param2,param3 + 1);
            }
            if("btnOpenStack" in param1)
            {
               this.A11yCollectFocusables(Object(param1)["btnOpenStack"] as DisplayObject,param2,param3 + 1);
            }
            return;
         }
         _loc4_ = param1 as DisplayObjectContainer;
         if(_loc4_ != null)
         {
            _loc5_ = 0;
            while(_loc5_ < _loc4_.numChildren)
            {
               this.A11yCollectFocusables(_loc4_.getChildAt(_loc5_),param2,param3 + 1);
               _loc5_++;
            }
         }
      }

      public function A11ySortBounds(item:DisplayObject) : Rectangle
      {
         var name:String = getQualifiedClassName(item);
         try
         {
            // Lot thumbnails contain transparent margins. EA already measures
            // the visible house into this invisible tooltip anchor.
            if(name == "widgets.GameEntry.Neighborhood.controls::LotClip" || name == "widgets.GameEntry.Neighborhood.controls::MultiUnitLotClip" || name == "widgets.GameEntry.Neighborhood.controls::StreetTaggedLotClip" || ("mcTooltipDummy" in item && "lotId" in item && "GetData" in item && "mcPositionHelper" in item && "mcMapTag" in item))
            {
               var anchor:DisplayObject = Object(item)["mcTooltipDummy"] as DisplayObject;
               if(anchor != null && anchor.stage != null)
               {
                  var lotBounds:Rectangle = anchor.getBounds(item.stage);
                  if(lotBounds.width > 2 && lotBounds.height > 2) { return lotBounds; }
               }
            }
            // Map toolbar hover timelines enlarge artwork around the hit area.
            // Sort by EA's stable interaction bounds so Tab does not loop.
            if((name.indexOf("widgets.GameTray.controls::") == 0 || name.indexOf("widgets.GameEntry.WorldSelection::") == 0) && "GetBoundsOverride" in item)
            {
               return Object(item)["GetBoundsOverride"](item.stage) as Rectangle;
            }
         }
         catch(e:Error) { }
         return item.getBounds(item.stage);
      }

      // Simplified Game Options only: the category ButtonBar and each native
      // setting list sort as one block, so the category column never
      // interleaves with the settings beside it (2026-09-26 live: Graphics,
      // Audio, then the Graphics setting Windowed; Up from Gameplay entered a
      // settings list from below). Other scopes and simplified off are unchanged.
      public function A11yOptionsScoped() : Boolean
      {
         try
         {
            return this.mA11ySimplifiedMenus && this.mA11yScope != null && getQualifiedClassName(this.mA11yScope).indexOf("widgets.OptionsMenu::") == 0 && this.A11ySimplifiedActive();
         }
         catch(e:Error) { }
         return false;
      }

      public function A11ySortBlock(item:DisplayObject) : DisplayObject
      {
         var node:DisplayObject = null;
         var depth:int = 0;
         var list:Object = null;
         var block:DisplayObject = null;
         try
         {
            if(item == null || !this.A11yOptionsScoped()) { return item; }
            node = item.parent;
            while(node != null && depth < 14 && node != this.mA11yScope)
            {
               if(getQualifiedClassName(node) == "scaleform.clik.controls::ButtonBar") { return node; }
               node = node.parent;
               depth = depth + 1;
            }
            list = this.A11yFindScrollList(item);
            block = list as DisplayObject;
            if(block != null && block != item) { return block; }
         }
         catch(e:Error) { }
         return item;
      }

      public function A11ySortFocusables(param1:DisplayObject, param2:DisplayObject) : Number
      {
         if(param1 is DisplayObjectContainer && DisplayObjectContainer(param1).contains(param2)) { return -1; }
         if(param2 is DisplayObjectContainer && DisplayObjectContainer(param2).contains(param1)) { return 1; }
         var blockA:DisplayObject = this.A11ySortBlock(param1);
         var blockB:DisplayObject = this.A11ySortBlock(param2);
         if(blockA != blockB)
         {
            param1 = blockA;
            param2 = blockB;
         }
         var _loc3_:Rectangle = this.A11ySortBounds(param1);
         var _loc4_:Rectangle = this.A11ySortBounds(param2);
         if(Math.abs(_loc3_.y - _loc4_.y) > 6)
         {
            return _loc3_.y < _loc4_.y ? -1 : 1;
         }
         if(Math.abs(_loc3_.x - _loc4_.x) > 2)
         {
            return _loc3_.x < _loc4_.x ? -1 : 1;
         }
         var _loc5_:String = getQualifiedClassName(param1) + "/" + param1.name;
         var _loc6_:String = getQualifiedClassName(param2) + "/" + param2.name;
         if(_loc5_ == _loc6_)
         {
            return 0;
         }
         return _loc5_ < _loc6_ ? -1 : 1;
      }

      // 2026-09-24: CAS keeps GameTray buttons live but off the stage (x>1800 on
      // a 1693 px stage: Help Center, Floor Buttons, Scenario Requirements).
      // Leaf eligibility only; containers and list scrolling are untouched.
      public function A11yIntersectsStage(item:DisplayObject) : Boolean
      {
         var bounds:Rectangle = null;
         try
         {
            if(item == null || item.stage == null) { return false; }
            bounds = item.getBounds(item.stage);
            return bounds.right > 0 && bounds.bottom > 0 && bounds.left < item.stage.stageWidth && bounds.top < item.stage.stageHeight;
         }
         catch(e:Error) { }
         return false;
      }

      // Match the static scrollers that A11yRevealControl can reveal on focus.
      public function A11yCanRevealOnStage(item:DisplayObject) : Boolean
      {
         var node:Object = item != null ? item.parent : null;
         var view:DisplayObject = null;
         var slider:Object = null;
         var mask:DisplayObject = null;
         try
         {
            while(node != null)
            {
               view = null;
               slider = null;
               if("mScrollerView" in node && "mSlider" in node) { view = node["mScrollerView"] as DisplayObject; slider = node["mSlider"]; }
               if("mcView" in node && "mcSlider" in node) { view = node["mcView"] as DisplayObject; slider = node["mcSlider"]; }
               if("mcScheduleView" in node && "mcScheduleSlider" in node) { view = node["mcScheduleView"] as DisplayObject; slider = node["mcScheduleSlider"]; }
               if("mcSaveListView" in node && "mcSaveListSlider" in node) { view = node["mcSaveListView"] as DisplayObject; slider = node["mcSaveListSlider"]; }
               if(view != null && slider != null && "mcMask" in view && this.A11yIsLive(view))
               {
                  mask = Object(view)["mcMask"] as DisplayObject;
                  if(this.A11yIntersectsStage(mask)) { return true; }
               }
               node = node.parent;
            }
         }
         catch(e:Error) { }
         return false;
      }

      public function A11yInListViewport(item:DisplayObject) : Boolean
      {
         // Static nested grids retain offscreen rows. Reveal them on focus;
         // recycled cells are traversed by their data index instead.
         return true;
      }

      public function A11yEnterNestedList(outer:Object, target:DisplayObject, direction:int) : Boolean
      {
         var inner:Object = null;
         var count:int = 0;
         try
         {
            inner = this.A11yFindScrollList(target);
            if(inner == null || outer == null || inner == outer || !this.A11yIsInside(inner as DisplayObject,outer as DisplayObject)) { return false; }
            count = int(this.A11yGridLayout(inner)["GetNumItems"]());
            if(count <= 0) { return false; }
            return this.A11yRequestIndex(inner,direction > 0 ? 0 : count - 1,direction);
         }
         catch(e:Error) { }
         return false;
      }

      public function A11yTabMove(param1:int) : void
      {
         var _loc2_:Array = null;
         var _loc3_:Stage = null;
         var _loc4_:int = 0;
         var _loc5_:DisplayObject = null;
         var _loc6_:DisplayObject = null;
         var _loc7_:Object = null;
         var _loc8_:int = 0;
         var _loc9_:Object = null;
         var _loc10_:int = -1;
         try
         {
            this.A11yModalFrame();
            if(this.mTooltipsLayer == null)
            {
               return;
            }
            _loc3_ = this.mTooltipsLayer.stage;
            if(_loc3_ == null)
            {
               return;
            }
            if(this.mA11yScope != null && this.mA11yScope.stage == null)
            {
               this.mA11yScope = null;
               this.mA11yList = null;
            }
            if(this.mA11yIdxDir != 0)
            {
               this.mA11yNavQueue.push(param1);
               return;
            }
            if(this.mA11yPendingScope != null) { this.mA11yNavQueue.push(param1); return; }
            _loc6_ = this.mA11yScope != null ? this.mA11yScope : _loc3_;
            if(this.mA11yScope != null) { this.mA11yList = null; }
            if(this.mA11yListRoot != _loc6_ || this.mA11yFocused == null || this.mA11yFocused.stage == null)
            {
               this.mA11yList = null;
            }
            if(this.mA11yList == null || this.mA11yList.length == 0)
            {
               _loc2_ = new Array();
               if(this.mA11yScope != null)
               {
                  this.A11yCollectFocusables(this.mA11yScope,_loc2_,0);
               }
               if(_loc2_.length == 0 && this.mA11yScope != null) { return; }
               if(_loc2_.length == 0)
               {
                  this.mA11yScope = null;
                  _loc6_ = _loc3_;
                  this.A11yCollectFocusables(_loc3_,_loc2_,0);
               }
               if(_loc2_.length == 0)
               {
                  return;
               }
               _loc2_.sort(this.A11ySortFocusables);
               this.mA11yList = _loc2_;
               this.mA11yListRoot = _loc6_;
            }
            _loc2_ = this.mA11yList;
            _loc4_ = -1;
            if(this.mA11yFocused != null)
            {
               _loc4_ = _loc2_.indexOf(this.mA11yFocused);
            }
            if(this.mA11yEdge != 0)
            {
               _loc4_ = this.mA11yEdge > 0 ? _loc2_.length - 1 : 0;
               this.mA11yEdge = 0;
            }
            else
            {
               // While focus is INSIDE a virtualized list, move by index
               // rather than by position in the collected focusable array.
               // The array only ever holds the VISIBLE rows, so walking it
               // reaches the footer after five rows and never sees row six;
               // and because cells are RECYCLED, array entries go stale the
               // moment the list scrolls. A11yStepInList returns false only
               // when the step would genuinely leave the list, which is
               // when the normal walk below should take over and move on to
               // the footer.
               _loc7_ = this.A11yFindScrollList(this.mA11yFocused);
               if(_loc7_ != null && _loc4_ >= 0)
               {
                  _loc8_ = _loc4_ + param1;
                  // Visit a row's secondary control before advancing data.
                  if(_loc8_ >= 0 && _loc8_ < _loc2_.length && this.A11yFindScrollList(_loc2_[_loc8_]) == _loc7_ && this.A11yCellIndexOf(this.A11yGridLayout(_loc7_),_loc2_[_loc8_]) == this.mA11yLogicalIndex)
                  {
                     this.A11yFocusItem(_loc2_[_loc8_]);
                     return;
                  }
                  // A list nested in this list's rows (event planner: each
                  // world row holds its venue list): enter it before stepping
                  // the outer list (2026-09-26 live: Down from Willow Creek
                  // skipped its four visible venues to Henford-on-Bagley).
                  if(_loc8_ >= 0 && _loc8_ < _loc2_.length && this.A11yEnterNestedList(_loc7_,_loc2_[_loc8_],param1))
                  {
                     return;
                  }
                  if(this.A11yStepInList(param1))
                  {
                     return;
                  }
               }
               _loc4_ = _loc4_ + param1;
               if(_loc4_ >= _loc2_.length)
               {
                  if(this.A11yIndexScroll(1,false))
                  {
                     return;
                  }
                  _loc4_ = 0;
               }
               else if(_loc4_ < 0)
               {
                  if(this.A11yIndexScroll(-1,false))
                  {
                     return;
                  }
                  _loc4_ = _loc2_.length - 1;
               }
            }
            _loc5_ = _loc2_[_loc4_];
            _loc7_ = this.A11yFindScrollList(_loc5_);
            _loc9_ = this.A11yFindScrollList(this.mA11yFocused);
            if(_loc7_ != null && _loc7_ != _loc9_)
            {
               _loc8_ = param1 > 0 ? 0 : int(this.A11yGridLayout(_loc7_)["GetNumItems"]()) - 1;
               // Leaving a nested list back into the list that holds it
               // continues at the adjacent row, not at that list's first or
               // last row (which would restart at the first world).
               if(_loc9_ != null && this.A11yIsInside(_loc9_ as DisplayObject,_loc7_ as DisplayObject))
               {
                  _loc10_ = this.A11yCellIndexOf(this.A11yGridLayout(_loc7_),_loc5_);
                  if(_loc10_ >= 0) { _loc8_ = _loc10_; }
               }
               if(_loc8_ >= 0 && this.A11yRequestIndex(_loc7_,_loc8_,param1)) { return; }
            }
            this.A11yFocusItem(_loc5_);
         }
         catch(e:Error)
         {
         }
      }

      public var mA11ySyntheticHover:Boolean = false;

      public function A11yFocusHover(param1:DisplayObject, param2:DisplayObject) : void
      {
         this.mA11ySyntheticHover = true;
         try
         {
            if(param1 != param2 && param1 != null) { this.HideTooltips(true); }
            param1 = this.A11yHoverProxy(param1);
            param2 = this.A11yHoverProxy(param2);
            if(param1 != null && param1 != param2 && !(param2 != null && param1 is DisplayObjectContainer && DisplayObjectContainer(param1).contains(param2)))
            {
               // Moving into a row's Remove button must not hide it.
               if(param1.parent != null && "btnRemove" in param1.parent && Object(param1.parent)["btnRemove"] == param1 && param1.parent != param2)
               {
                  param1.parent.dispatchEvent(new MouseEvent(MouseEvent.ROLL_OUT,false,false));
               }
               param1.dispatchEvent(new MouseEvent(MouseEvent.ROLL_OUT,false,false));
               param1.dispatchEvent(new MouseEvent(MouseEvent.MOUSE_OUT,true,false));
            }
            if(param2 != null)
            {
               param2.dispatchEvent(new MouseEvent(MouseEvent.ROLL_OVER,false,false));
               param2.dispatchEvent(new MouseEvent(MouseEvent.MOUSE_OVER,true,false));
            }
         }
         catch(e:Error)
         {
         }
         this.mA11ySyntheticHover = false;
      }

      public function A11yFenceOpeningInput() : void
      {
         try
         {
            this.mA11yStartupKeys.length = 0;
            this.A11yPostToPython("a11y.inputfence","");
         }
         catch(e:Error) { }
      }

      public function A11yFocusInto(param1:DisplayObject) : void
      {
         try
         {
            if(param1 == null || this.mTooltipsLayer == null)
            {
               return;
            }
            if(!this.mA11yKeyboard) { return; }
            if(param1 == this.mA11yScope && this.mA11yPendingScope == null)
            {
               this.mA11yList = null;
               return;
            }
            this.A11yCancelIndex();
            if(this.mA11yPendingScope != param1) { this.A11yFenceOpeningInput(); }
            this.mA11yPendingScope = param1;
            this.mA11yScopeTries = 0;
            // Calendar supplies its weather after the initial layout. Give
            // that update a short window before announcing the header.
            this.mA11yScopeReadyAt = getTimer() + (getQualifiedClassName(param1).indexOf("CalendarMain") >= 0 ? 300 : 0);
            this.mTooltipsLayer.addEventListener(Event.ENTER_FRAME,this.A11yScopeFrame,false,0,true);
         }
         catch(e:Error)
         {
         }
      }

      public function A11yScopeFrame(param1:Event) : void
      {
         var _loc2_:Array = null;
         var resumed:Boolean = false;
         var historyIndex:int = -1;
         var returning:Boolean = false;
         try
         {
            this.mA11yScopeTries++;
            // 24 frames (well under a second) was too tight for pickers
            // whose rows arrive only after the game answers the widget's
            // PickerSet message; the scope was abandoned before the rows
            // existed and focus fell back to the whole stage. This only
            // costs an idle ENTER_FRAME while waiting, and stops the
            // moment a focusable appears.
            if(this.mA11yPendingScope == null || this.mA11yScopeTries > 150)
            {
               this.mTooltipsLayer.removeEventListener(Event.ENTER_FRAME,this.A11yScopeFrame);
               if(this.A11yIsLive(this.mA11yPendingScope)) { this.mA11yScope = this.mA11yPendingScope; }
               this.mA11yPendingScope = null;
               this.mA11yNavQueue.length = 0;
               return;
            }
            if(this.mA11yPendingScope.stage == null)
            {
               return;
            }
            if(this.mA11yScopeTries < 3) { return; }
            if(getTimer() < this.mA11yScopeReadyAt) { return; }
            if(this.mA11yPendingScope == this.mA11yHudRoot && "mcPanel" in this.mA11yPendingScope)
            {
               var panel:Object = Object(this.mA11yPendingScope)["mcPanel"];
               if(panel != null && "SetSize" in panel) { panel["SetSize"](Number(panel["width"]),this.mA11yPendingScope.stage.stageHeight,false); }
            }
            _loc2_ = new Array();
            this.mA11yMotiveLinks = new Dictionary(true);
            this.A11yIndexMotiveLinks(this.mA11yPendingScope);
            this.A11yCollectFocusables(this.mA11yPendingScope,_loc2_,0);
            if(_loc2_.length == 0)
            {
               return;
            }
            this.mTooltipsLayer.removeEventListener(Event.ENTER_FRAME,this.A11yScopeFrame);
            historyIndex = this.mA11yScopeHistory.length - 1;
            while(historyIndex >= 0)
            {
               if(this.mA11yScopeHistory[historyIndex].scope == this.mA11yPendingScope)
               {
                  returning = true;
                  if(!this.A11yIsLive(this.mA11yResumeFocus) || !this.A11yIsInside(this.mA11yResumeFocus,this.mA11yPendingScope)) { this.mA11yResumeFocus = this.mA11yScopeHistory[historyIndex].focus; }
                  this.mA11yScopeHistory.length = historyIndex;
                  break;
               }
               historyIndex = historyIndex - 1;
            }
            if(!returning && this.mA11yScope != null && this.mA11yScope != this.mA11yPendingScope && this.A11yIsLive(this.mA11yScope))
            {
               this.mA11yScopeHistory.push({scope:this.mA11yScope,focus:this.mA11yFocused});
            }
            this.mA11yScope = this.mA11yPendingScope;
            this.mA11yPendingScope = null;
            this.A11yFocusHover(this.mA11yFocused,null);
            this.mA11yFocused = null;
            this.mA11yList = null;
            this.mA11yOpening = true;
            if(this.mA11yAutoFocus)
            {
               if(this.mA11yResumeFocus != null && this.A11yIsLive(this.mA11yResumeFocus) && this.A11yIsInside(this.mA11yResumeFocus,this.mA11yScope))
               {
                  resumed = true;
                  this.A11yFocusItem(this.mA11yResumeFocus);
                  this.mA11yResumeFocus = null;
               }
               else if(this.mA11yScope == this.mA11yDropdown) { this.A11yFocusDropdown(); }
               else if(this.A11yFocusPhoneApp(_loc2_)) { }
               else if(this.mA11yScope == this.mA11yStatusScope && "mcMoodContainer" in this.mA11yScope)
               {
                  this.A11yFocusItem(Object(this.mA11yScope)["mcMoodContainer"]);
               }
               else { this.A11yInitialFocus(_loc2_); }
            }
            this.mA11yOpening = false;
            this.mA11yFocusPending = null;
            if(resumed) { this.A11yReadCurrent(); }
            else { this.A11yAnnounceScope(); }
            this.A11yDrainNav();
         }
         catch(e:Error) { this.mA11yOpening = false; }
      }

      public function A11yTryScroll(param1:int) : Boolean
      {
         var _loc2_:DisplayObject = null;
         var _loc3_:int = 0;
         var _loc4_:String = null;
         var _loc5_:Object = null;
         try
         {
            if(this.mA11yScrollDir != 0)
            {
               return false;
            }
            _loc5_ = this.A11yFindSlider(this.mA11yFocused);
            if(_loc5_ != null)
            {
               if(!this.A11yStepSlider(_loc5_,param1))
               {
                  return false;
               }
               this.A11yBeginScroll(param1);
               return true;
            }
            _loc2_ = this.mA11yFocused;
            while(_loc2_ != null && _loc3_ < 12)
            {
               _loc4_ = getQualifiedClassName(_loc2_);
               if(_loc2_.scrollRect != null || _loc4_.indexOf("Scroll") >= 0 || _loc4_.indexOf("GridView") >= 0 || _loc4_.indexOf("ListView") >= 0)
               {
                  _loc2_.dispatchEvent(new MouseEvent(MouseEvent.MOUSE_WHEEL,true,false,0,0,null,false,false,false,false,param1 > 0 ? -3 : 3));
                  this.A11yBeginScroll(param1);
                  return true;
               }
               _loc2_ = _loc2_.parent;
               _loc3_++;
            }
         }
         catch(e:Error)
         {
         }
         return false;
      }

      public function A11yBeginScroll(param1:int) : void
      {
         this.mA11yScrollAnchor = this.mA11yList != null && this.mA11yList.length > 0 ? this.mA11yList[0] : null;
         this.mA11yPrevList = this.mA11yList;
         this.mA11yScrollDir = param1;
         this.mA11yScrollTries = 0;
         if(this.mTooltipsLayer != null)
         {
            this.mTooltipsLayer.addEventListener(Event.ENTER_FRAME,this.A11yScrollFrame,false,0,true);
         }
      }

      public function A11yFindSlider(param1:DisplayObject) : Object
      {
         var _loc2_:DisplayObject = param1;
         var _loc3_:int = 0;
         var _loc4_:Object = null;
         var _loc5_:Object = null;
         while(_loc2_ != null && _loc3_ < 14)
         {
            try
            {
               _loc4_ = _loc2_;
               _loc5_ = _loc4_["mSlider"];
               if(_loc5_ != null && _loc5_["MaxValue"] > _loc5_["MinValue"])
               {
                  return _loc5_;
               }
            }
            catch(e:Error)
            {
            }
            _loc2_ = _loc2_.parent;
            _loc3_++;
         }
         return null;
      }

      public function A11yStepSlider(param1:Object, param2:int) : Boolean
      {
         var _loc3_:Number = NaN;
         var _loc4_:Number = NaN;
         var _loc5_:Number = NaN;
         var _loc6_:Number = NaN;
         try
         {
            _loc3_ = Number(param1["Value"]);
            _loc4_ = Number(param1["MinValue"]);
            _loc5_ = Number(param1["MaxValue"]);
            if(!(_loc5_ > _loc4_))
            {
               return false;
            }
            _loc6_ = _loc3_ + param2 * Math.max(1,(_loc5_ - _loc4_) * 0.06);
            if(_loc6_ < _loc4_)
            {
               _loc6_ = _loc4_;
            }
            if(_loc6_ > _loc5_)
            {
               _loc6_ = _loc5_;
            }
            if(Math.abs(_loc6_ - _loc3_) < 0.0001)
            {
               return false;
            }
            param1["SetCurrentValue"](_loc6_,true,true,true);
            return true;
         }
         catch(e:Error)
         {
         }
         return false;
      }

      public function A11yFirstNewItem(param1:Array, param2:int) : DisplayObject
      {
         var _loc3_:int = 0;
         var _loc4_:DisplayObject = null;
         if(this.mA11yPrevList == null)
         {
            return null;
         }
         if(param2 > 0)
         {
            _loc3_ = 0;
            while(_loc3_ < param1.length)
            {
               _loc4_ = param1[_loc3_];
               if(this.mA11yPrevList.indexOf(_loc4_) < 0)
               {
                  return _loc4_;
               }
               _loc3_++;
            }
         }
         else
         {
            _loc3_ = param1.length - 1;
            while(_loc3_ >= 0)
            {
               _loc4_ = param1[_loc3_];
               if(this.mA11yPrevList.indexOf(_loc4_) < 0)
               {
                  return _loc4_;
               }
               _loc3_--;
            }
         }
         return null;
      }

      public function A11yFocusItem(param1:DisplayObject) : void
      {
         try
         {
            if(!this.mA11yKeyboard) { return; }
            param1 = this.A11ySemanticTarget(param1);
            this.A11yHoldPointerSpeech();
            if(this.mA11yLogicalList != null && this.mA11yLogicalList != this.A11yFindScrollList(param1))
            {
               this.mA11yReturnList = this.mA11yLogicalList;
               this.mA11yReturnIndex = this.mA11yLogicalIndex;
               this.mA11yListMemory[this.mA11yLogicalList] = this.mA11yLogicalIndex;
            }
            this.A11yRevealControl(param1);
            this.A11yFocusHover(this.mA11yFocused,param1);
            this.A11yWatchFocused(this.mA11yFocused,param1);
            this.mA11yFocused = param1;
            this.mA11yLastWidget = param1;
            this.mA11yLogicalList = this.A11yFindScrollList(param1);
            this.mA11yLogicalIndex = this.mA11yLogicalList != null ? this.A11yCellIndexOf(this.A11yGridLayout(this.mA11yLogicalList),param1) : -1;
            if(param1 != null && param1.stage != null)
            {
               param1.stage.focus = param1 is TextField && TextField(param1).type == "input" ? TextField(param1) : null;
            }
            this.A11yDrawFocusRing(param1);
            if(param1 != null && "A11yAnnounceMood" in param1) { Object(param1)["A11yAnnounceMood"](); }
            else { this.A11yAnnounceDisplay(param1,"a11y.widget_enc",false); }
            // Settled re-reading corrects fast list scrolling. Informational
            // icons retain their existing hover narration without a second
            // generic label canceling a richer tooltip.
            this.mA11yFocusPending = this.mA11yLogicalList != null ? param1 : null;
            this.mA11yFocusDue = getTimer() + 180;
         }
         catch(e:Error)
         {
         }
      }

      public function A11yScrollFrame(param1:Event) : void
      {
         var _loc2_:int = 0;
         var _loc3_:Array = null;
         var _loc4_:DisplayObject = null;
         var _loc5_:DisplayObject = null;
         try
         {
            this.mA11yScrollTries++;
            if(this.mA11yScrollTries < 3)
            {
               return;
            }
            this.mTooltipsLayer.removeEventListener(Event.ENTER_FRAME,this.A11yScrollFrame);
            _loc2_ = this.mA11yScrollDir;
            this.mA11yScrollDir = 0;
            _loc3_ = new Array();
            _loc4_ = this.mA11yScope != null ? this.mA11yScope : this.mTooltipsLayer.stage;
            this.A11yCollectFocusables(_loc4_,_loc3_,0);
            _loc3_.sort(this.A11ySortFocusables);
            this.mA11yList = null;
            this.mA11yFocused = null;
            if(_loc3_.length > 0 && this.mA11yScrollAnchor != null && _loc3_[0] == this.mA11yScrollAnchor)
            {
               this.mA11yEdge = 0;
               this.mA11yPrevList = null;
               this.mA11yScrollAnchor = null;
               this.A11yTabMove(_loc2_);
               return;
            }
            _loc5_ = this.A11yFirstNewItem(_loc3_,_loc2_);
            this.mA11yScrollAnchor = null;
            this.mA11yPrevList = null;
            if(_loc5_ != null)
            {
               this.mA11yList = _loc3_;
               this.mA11yListRoot = _loc4_;
               this.mA11yEdge = 0;
               this.A11yFocusItem(_loc5_);
               return;
            }
            this.mA11yEdge = _loc2_ > 0 ? 1 : -1;
            this.A11yTabMove(_loc2_);
         }
         catch(e:Error)
         {
            this.mA11yScrollDir = 0;
         }
      }

      public function A11yIsInside(item:DisplayObject, root:DisplayObject) : Boolean
      {
         // DisplayObjectContainer.contains(null) throws ArgumentError.
         // A missing previous scope is normal on the first panel open.
         // Let ownership finish entering the new scope instead of aborting
         // after its keyboard guard has already been enabled.
         if(item == null || root == null) { return false; }
         return item == root || root is DisplayObjectContainer && DisplayObjectContainer(root).contains(item);
      }

      public function A11yCurrentDropdown() : DisplayObject
      {
         try
         {
            var type:Object = getDefinitionByName("olympus.extensions.DropdownExtension");
            var list:DisplayObject = type["GetCurrentDropdownList"]();
            return this.A11yIsLive(list) ? list : null;
         }
         catch(e:Error) { }
         return null;
      }

      public function A11yFindDropdownExtension(item:DisplayObject, list:DisplayObject) : Object
      {
         var type:Object = null;
         var extension:Object = null;
         var candidates:Array = new Array();
         var node:DisplayObject = item;
         var actionTarget:DisplayObject = null;
         try
         {
            type = getDefinitionByName("olympus.extensions.DropdownExtension");
            while(node != null)
            {
               if("GetExtension" in node) { extension = type["Get"](node,false); if(extension != null && extension["DropdownList"] == list) { return extension; } }
               // Semantic fields can activate a child button. Its extension
               // also owns selected data and Close; retain that same owner
               // when the popup is opened from the keyboard wrapper.
               actionTarget = this.A11yActionProxy(node);
               if(actionTarget != null && actionTarget != node && "GetExtension" in actionTarget) { extension = type["Get"](actionTarget,false); if(extension != null && extension["DropdownList"] == list) { return extension; } }
               node = node.parent;
            }
            this.A11yCollectFocusables(this.mA11yScope,candidates,0);
            for each(node in candidates)
            {
               if("GetExtension" in node) { extension = type["Get"](node,false); if(extension != null && extension["DropdownList"] == list) { return extension; } }
               actionTarget = this.A11yActionProxy(node);
               if(actionTarget != null && actionTarget != node && "GetExtension" in actionTarget) { extension = type["Get"](actionTarget,false); if(extension != null && extension["DropdownList"] == list) { return extension; } }
            }
         }
         catch(e:Error) { }
         return null;
      }

      public function A11yFocusDropdown() : void
      {
         var layout:Object = this.A11yGridLayout(this.mA11yDropdown);
         var feed:Object = layout["GetDataFeed"]();
         var selected:Object = this.mA11yDropdownExtension != null ? this.mA11yDropdownExtension["SelectedData"] : null;
         var index:int = 0;
         var count:int = int(layout["GetNumItems"]());
         while(index < count)
         {
            if(feed["RequestItemAt"](index) == selected) { break; }
            index = index + 1;
         }
         this.A11yRequestIndex(this.mA11yDropdown,index < count ? index : 0,1);
      }

      public function A11yFocusPhoneApp(items:Array) : Boolean
      {
         var item:DisplayObject = null;
         if(this.mA11yScope == null || getQualifiedClassName(this.mA11yScope).indexOf("PhonePanel") < 0) { return false; }
         items.sort(this.A11ySortFocusables);
         for each(item in items)
         {
            if(getQualifiedClassName(item).indexOf("PhoneCategoryCellView") >= 0) { this.A11yFocusItem(item); return true; }
         }
         return false;
      }

      public function A11yIntroText(item:DisplayObject, result:Array, depth:int = 0) : void
      {
         if(item == null || !item.visible || depth > 20 || result.length > 40 || this.A11yKeyboardDecoration(item)) { return; }
         if(item is TextField) { this.A11yCollectText(item,result,0,true); return; }
         if(depth > 0 && this.A11yIsFocusable(item)) { return; }
         var container:DisplayObjectContainer = item as DisplayObjectContainer;
         var index:int = 0;
         if(container == null) { return; }
         while(index < container.numChildren) { this.A11yIntroText(container.getChildAt(index),result,depth + 1); index = index + 1; }
      }

      public function A11yAnnounceScope() : void
      {
         var intro:Array = new Array();
         var focus:Array = new Array();
         var title:String = "";
         var kind:String = "";
         try
         {
            if(this.mA11yScope == this.mA11yDropdown) { this.A11yReadCurrent(); return; }
            if(this.mA11yScope == this.mA11yHudRoot && this.mA11yHudButton != null)
            {
               if("TooltipExt" in this.mA11yHudButton) { title = String(Object(this.mA11yHudButton)["TooltipExt"]["Text"]); }
               if(title != "null" && title.length > 0) { intro.push("0|0|" + title); }
            }
            else if(this.mA11yManagedDialog != null && this.A11yIsInside(this.mA11yScope,this.mA11yManagedDialog))
            {
               kind = "dialog";
               this.A11yIntroText(this.mA11yScope,intro);
            }
            else if(this.mA11yScope != null && (getQualifiedClassName(this.mA11yScope).indexOf("HolidaySettingsMain") >= 0 || getQualifiedClassName(this.mA11yScope).indexOf("PickersMain") >= 0 || getQualifiedClassName(this.mA11yScope) == "widgets.GameEntry.RentalPanel::GERentalPanelMain" || getQualifiedClassName(this.mA11yScope) == "widgets.CAS.Stories::CASStoriesDialog" || getQualifiedClassName(this.mA11yScope) == "widgets.GameEntry.WorldSelection.SeasonSelect::SeasonSelectContainer"))
            {
               kind = "dialog";
               this.A11yIntroText(this.mA11yScope,intro);
            }
            else { this.A11yReadCurrent(); return; }
            this.A11yCollectText(this.mA11yFocused,focus,0,true);
            if(this.mA11yFocused != null && "A11yMotiveText" in this.mA11yFocused) { focus = ["0|0|" + Object(this.mA11yFocused)["A11yMotiveText"]()]; }
            if(this.mA11yFocused != null && "TooltipExt" in this.mA11yFocused && Object(this.mA11yFocused)["TooltipExt"]["Text"] != null) { focus.push("99999|0|" + String(Object(this.mA11yFocused)["TooltipExt"]["Text"])); }
            var encoded:String = encodeURIComponent(kind + "\u0002" + intro.join("\u0001") + "\u0002" + focus.join("\u0001"));
            encoded = encoded.split("'").join("%27").split("(").join("%28").split(")").join("%29").split("!").join("%21");
            this.A11yPostToPython("a11y.scope_enc",encoded);
         }
         catch(e:Error) { }
      }

      public function A11yRentalQuote(item:DisplayObject, result:Array) : void
      {
         var node:DisplayObject = item;
         var panel:Object = null;
         var depth:int = 0;
         var field:String = "";
         try
         {
            while(node != null && depth < 12)
            {
               // The live movie instantiates the exported GERentalPanel symbol,
               // a subclass of the shared RentalPanel control.
               if(getQualifiedClassName(node) == "GERentalPanel" || getQualifiedClassName(node) == "widgets.GameEntry.RentalPanel.controls::RentalPanel") { panel = node; break; }
               node = node.parent;
               depth = depth + 1;
            }
            if(panel == null) { return; }
            // Read EA's current localized quote when returning from the duration
            // list and before confirming. Popup rows keep their own labels.
            if(!this.A11yIsInside(item,panel["ddRentalTime"]) && !this.A11yIsInside(item,panel["btnOkayCreate"]) && !this.A11yIsInside(item,panel["btnOkayExtend"])) { return; }
            for each(field in ["txtRentFor","ddRentalTime","txtDays","txtCostCalculator","txtCost"])
            {
               node = panel[field] as DisplayObject;
               if(node != null && node.visible) { this.A11yCollectText(node,result,0,true); }
            }
         }
         catch(e:Error) { }
      }

      public function A11yFundsTarget(item:DisplayObject) : Boolean
      {
         var depth:int = 0;
         while(item != null && depth < 5)
         {
            if(item.name == "mcSimoleonWallet") { return true; }
            item = item.parent;
            depth = depth + 1;
         }
         return false;
      }

      public function A11ySetSilentMood(text:String) : void
      {
         var field:TextField = new TextField();
         field.htmlText = text;
         this.mA11ySilentMood = field.text;
      }

      public function A11yMoveInQuote(item:DisplayObject, result:Array) : void
      {
         var node:DisplayObject = item;
         var panel:Object = null;
         var depth:int = 0;
         var name:String = "";
         var field:String = "";
         try
         {
            while(node != null && depth < 12)
            {
               name = getQualifiedClassName(node);
               if(name == "widgets.GameEntry.MovePanel.controls::MoveInPanel" || name == "widgets.GameEntry.MovePanel.controls::PlexLotMoveInPanel" || name == "widgets.GameEntry.MovePanel.controls::MultiUnitMoveInPanel") { panel = node; break; }
               node = node.parent;
               depth = depth + 1;
            }
            if(panel == null) { return; }
            if(!this.A11yIsInside(item,panel["ddInOptions"]) && !this.A11yIsInside(item,panel["ddOutOptions"]) && !this.A11yIsInside(item,panel["btnOkay"])) { return; }
            // The native fields supply current furnishing choices and the
            // localized remaining balance, including unaffordable choices.
            for each(field in ["ddOutOptions","ddInOptions","txtRemainingFunds"])
            {
               node = panel[field] as DisplayObject;
               if(this.A11yIsLive(node)) { this.A11yCollectText(node,result,0,true); }
            }
         }
         catch(e:Error) { }
      }

      // Plain text of a control, without the y|x| layout prefixes.
      public function A11yJoinedText(node:DisplayObject) : String
      {
         var parts:Array = new Array();
         var words:Array = new Array();
         var entry:String = "";
         var cut:int = 0;
         var index:int = 0;
         try
         {
            if(!this.A11yIsLive(node)) { return ""; }
            this.A11yCollectText(node,parts,0,true);
            while(index < parts.length)
            {
               entry = String(parts[index]);
               cut = entry.indexOf("|",entry.indexOf("|") + 1);
               words.push(cut >= 0 ? entry.substr(cut + 1) : entry);
               index = index + 1;
            }
         }
         catch(e:Error) { }
         return words.join(" ");
      }

      // Household Split and Merge (TransferPanel), the shared Transfer Funds
      // panel and the retail Transfer Funds dialog show direction only as
      // arrows and artwork. Name both ends; Python words the \u0002dir\u0002
      // markers in the player's language (2026-10-04, Leo: players could not
      // tell where money or Sims were going). The left household is EA's
      // source (txtSourceFamily, mcLeftFunds); btnTransferRight moves money
      // left to right and btnTransferLeft right to left; btnTransferTo moves
      // the source panel's selected Sims to the target panel.
      public function A11yTransferQuote(item:DisplayObject, result:Array) : void
      {
         var node:DisplayObject = item;
         var panel:Object = null;
         var funds:Object = null;
         var retail:Object = null;
         var depth:int = 0;
         var left:String = "";
         var right:String = "";
         var leftFunds:String = "";
         var rightFunds:String = "";
         try
         {
            while(node != null && depth < 14)
            {
               if(funds == null && "btnTransferLeft" in node && "btnTransferRight" in node && "txtSourceFamily" in node) { funds = node; }
               if(panel == null && "btnTransferTo" in node && "btnTransferFrom" in node && "mcSourceHousehold" in node) { panel = node; }
               if(retail == null && "ddFrom" in node && "ddTo" in node && "btnSwap" in node) { retail = node; }
               node = node.parent;
               depth = depth + 1;
            }
            if(funds != null)
            {
               left = TextField(funds["txtSourceFamily"]).text;
               right = TextField(funds["txtTargetFamily"]).text;
               leftFunds = this.A11yJoinedText(funds["mcLeftFunds"] as DisplayObject);
               rightFunds = this.A11yJoinedText(funds["mcRightFunds"] as DisplayObject);
               if(this.A11yIsInside(item,funds["btnTransferRight"])) { result.push("0|0|\u0002dir\u0002funds\u0002" + left + "\u0002" + right); }
               else if(this.A11yIsInside(item,funds["btnTransferLeft"])) { result.push("0|0|\u0002dir\u0002funds\u0002" + right + "\u0002" + left); }
               else if(this.A11yIsInside(item,funds["txtAmount"])) { result.push("0|0|" + TextField(funds["txtAmountLabel"]).text); }
               else { funds = null; }
               if(funds != null)
               {
                  result.push("99000|0|\u0002dir\u0002has\u0002" + left + "\u0002" + leftFunds);
                  result.push("99999|0|\u0002dir\u0002has\u0002" + right + "\u0002" + rightFunds);
                  return;
               }
            }
            if(panel != null)
            {
               left = TextField(panel["mcSourceHousehold"]["txtHouseholdName"]).text;
               right = TextField(panel["mcTargetHousehold"]["txtHouseholdName"]).text;
               if(this.A11yIsInside(item,panel["btnTransferTo"])) { result.push("0|0|\u0002dir\u0002sims\u0002" + left + "\u0002" + right); }
               else if(this.A11yIsInside(item,panel["btnTransferFrom"])) { result.push("0|0|\u0002dir\u0002sims\u0002" + right + "\u0002" + left); }
               else if(this.A11yIsInside(item,panel["mcSourceHousehold"]["slTransferSims"]) || this.A11yIsInside(item,panel["mcSourceHousehold"]["cbSellFurnishings"])) { result.push("99999|0|\u0002dir\u0002in\u0002" + left + "\u0002"); }
               else if(this.A11yIsInside(item,panel["mcTargetHousehold"]["slTransferSims"]) || this.A11yIsInside(item,panel["mcTargetHousehold"]["cbSellFurnishings"])) { result.push("99999|0|\u0002dir\u0002in\u0002" + right + "\u0002"); }
               return;
            }
            if(retail != null)
            {
               left = this.A11yJoinedText(retail["ddFrom"] as DisplayObject);
               right = this.A11yJoinedText(retail["ddTo"] as DisplayObject);
               if(this.A11yIsInside(item,retail["ddFrom"])) { result.push("0|0|\u0002dir\u0002from\u0002\u0002"); }
               else if(this.A11yIsInside(item,retail["ddTo"])) { result.push("0|0|\u0002dir\u0002to\u0002\u0002"); }
               else if(this.A11yIsInside(item,retail["txtAmountInput"])) { result.push("0|0|\u0002dir\u0002amount\u0002\u0002"); }
               else if(this.A11yIsInside(item,retail["btnConfirm"])) { result.push("99999|0|\u0002dir\u0002retail\u0002" + this.A11yJoinedText(retail["txtAmountTranslated"] as DisplayObject) + "\u0002" + left + "\u0002" + right); }
            }
         }
         catch(e:Error) { }
      }

      // The move dialog's furnishing dropdowns say only their choice; name
      // which home each one is for with the dialog's own labels.
      public function A11yMoveLabel(item:DisplayObject, result:Array) : void
      {
         var node:DisplayObject = item;
         var depth:int = 0;
         try
         {
            while(node != null && depth < 12)
            {
               if("ddOutOptions" in node && "ddInOptions" in node && "txtMoving" in node)
               {
                  if(this.A11yIsInside(item,node["ddOutOptions"])) { result.push("0|0|" + this.A11yJoinedText(node["txtMoving"] as DisplayObject)); }
                  else if(this.A11yIsInside(item,node["ddInOptions"]) && "txtInOptions" in node) { result.push("0|0|" + this.A11yJoinedText(node["txtInOptions"] as DisplayObject)); }
                  return;
               }
               node = node.parent;
               depth = depth + 1;
            }
         }
         catch(e:Error) { }
      }

      // Game Options rows keep their localized name in the cell's lbLabel; a
      // focused dropdown button says only its value (2026-09-26 live: the
      // Autonomy and Auto Age rows read as bare Off and Yes). Checkbox rows
      // are whole-cell stops that already read their label.
      public function A11yOptionsRowLabel(item:DisplayObject, result:Array) : void
      {
         var node:DisplayObject = item;
         var depth:int = 0;
         var label:Object = null;
         var field:TextField = null;
         var value:String = "";
         try
         {
            while(node != null && depth < 4)
            {
               if("lbLabel" in node && "ddDropdown" in node)
               {
                  if(!this.A11yIsInside(item,Object(node)["ddDropdown"] as DisplayObject)) { return; }
                  label = Object(node)["lbLabel"];
                  if(label == null || !label["visible"] || !("textField" in label)) { return; }
                  field = label["textField"] as TextField;
                  if(field != null) { value = this.A11yTextValue(field); }
                  if(value != null && value.length > 0) { result.unshift("-999998|0|" + value); }
                  return;
               }
               node = node.parent;
               depth = depth + 1;
            }
         }
         catch(e:Error) { }
      }

      public function A11yTextValue(field:TextField) : String
      {
         var tunables:Object = null;
         var keys:Object = null;
         var days:Array = new Array();
         var labels:Array = null;
         var style:Object = null;
         var index:int = 0;
         try
         {
            if(field.name == "txtWeek" && field.parent != null && getQualifiedClassName(field.parent).indexOf("JobTimeCellView") >= 0 && field.styleSheet != null)
            {
               tunables = getDefinitionByName("widgets.Gameplay.SimInfoHUD.constants.SimInfoCareerPanelTunables");
               keys = getDefinitionByName("olympus.localization.KeysGP");
               labels = tunables["DAYS_OF_THE_WEEK_CSS_LABELS"];
               while(index < labels.length)
               {
                  style = field.styleSheet.getStyle("." + labels[index]);
                  if(String(style.color).toLowerCase() == String(tunables["NORMAL_DAY_COLOR"]).toLowerCase() || String(style.color).toLowerCase() == String(tunables["TNS_NORMAL_DAY_COLOR"]).toLowerCase())
                  {
                     days.push(keys["CALENDAR_WEEKDAY_NAME"].toString({"date":{"date":(index + 6) % 7 + 1}}));
                  }
                  index = index + 1;
               }
               return "Work days: " + (days.length > 0 ? days.join(", ") : "None");
            }
         }
         catch(e:Error) { }
         return field.text;
      }


      public function A11yIndexMotiveLinks(root:DisplayObject, depth:int = 0) : void
      {
         if(root == null || !root.visible || depth > 32) { return; }
         var linked:DisplayObject = null;
         var nested:DisplayObject = null;
         var field:String = null;
         var childField:String = null;
         var container:DisplayObjectContainer = root as DisplayObjectContainer;
         var index:int = 0;
         if("A11yMotiveText" in root && "btnSolve" in root)
         {
            // EA links these clips to the row but places some of them as
            // siblings. An ancestry walk alone cannot recognize them.
            for each(field in ["btnSolve","mcBar","mcBuffIcon","mcArrows","txtTitle","mcBackground","hitArea"])
            {
               try
               {
                  linked = Object(root)[field] as DisplayObject;
                  if(linked != null && linked != root)
                  {
                     this.mA11yMotiveLinks[linked] = root;
                     for each(childField in ["mcIcon","mcImage"])
                     {
                        if(childField in linked)
                        {
                           nested = Object(linked)[childField] as DisplayObject;
                           if(nested != null && nested != root) { this.mA11yMotiveLinks[nested] = root; }
                        }
                     }
                  }
               }
               catch(linkError:Error) { }
            }
         }
         if(container != null)
         {
            while(index < container.numChildren) { this.A11yIndexMotiveLinks(container.getChildAt(index),depth + 1); index = index + 1; }
         }
      }

      public function A11ySingleFilterLabel(item:DisplayObject) : DisplayObject
      {
         var group:Object = item != null ? item.parent : null;
         try
         {
            if(group != null && "CanExpand" in group && "btnLabel" in group && "btnCheckBox" in group && !group["CanExpand"]() && this.A11yIsLive(group["btnLabel"]) && (item == group["btnLabel"] || item == group["btnCheckBox"]))
            {
               return group["btnLabel"] as DisplayObject;
            }
         }
         catch(e:Error) { }
         return null;
      }

      // Map artwork and sub-buttons back to the single semantic control.
      public function A11ySemanticTarget(item:DisplayObject) : DisplayObject
      {
         var node:DisplayObject = item;
         var i:int = 0;
         var nameLabel:DisplayObject = this.A11yCASNameLabel(item);
         if(nameLabel != null) { return nameLabel; }
         var calendarAdd:DisplayObject = this.A11yCalendarAddOwner(item);
         if(calendarAdd != null) { return calendarAdd; }
         while(node != null && i < 12)
         {
            if(this.mA11yMotiveLinks[node] != null) { return this.mA11yMotiveLinks[node] as DisplayObject; }
            if("txtInput" in node && "txtStatic" in node) { return node; }
            var filterLabel:DisplayObject = this.A11ySingleFilterLabel(node);
            if(filterLabel != null) { return filterLabel; }
            if("A11yMotiveText" in node || "btnSolve" in node) { return node; }
            if("btnCellView" in node && item.name != "btnOpenStack") { return node; }
            if(node != item && "mcFilterBubble" in node && "btnFilterPanel" in node && !this.A11yIsInside(item,Object(node)["mcFilterPanel"])) { return Object(node)["mcFilterBubble"] as DisplayObject; }
            node = node.parent;
            i = i + 1;
         }
         return item;
      }

      public function A11yFilterPopup(root:DisplayObject, depth:int = 0) : DisplayObject
      {
         if(root == null || depth > 32 || !root.visible || root.alpha <= 0.01) { return null; }
         if("mcFilterPanel" in root && "btnFilterPanel" in root)
         {
            var panel:Object = Object(root)["mcFilterPanel"];
            if(panel != null && panel["IsVisibleOrAnimatingIn"]) { return panel as DisplayObject; }
         }
         var container:DisplayObjectContainer = root as DisplayObjectContainer;
         var found:DisplayObject = null;
         var i:int = 0;
         if(container != null)
         {
            while(i < container.numChildren)
            {
               found = this.A11yFilterPopup(container.getChildAt(i),depth + 1);
               if(found != null) { return found; }
               i = i + 1;
            }
         }
         return null;
      }

      public function A11yKeyboardSuppress(event:Event) : void
      {
         // The native InputAction guard locks the camera. CLIK also has an
         // independent input dispatcher. Let it track raw down/up pairs,
         // then consume the processed event before FocusHandler sees it.
         // Suppressing only raw KEY_DOWN would corrupt keyHash on KEY_UP.
         var details:Object = Object(event)["details"];
         if(details == null || details["type"] != "key") { return; }
         var key:int = int(details["code"]);
         if([8,9,13,27,32,37,38,39,40].indexOf(key) < 0) { return; }
         if(this.A11yGuardValid(key))
         {
            Object(event)["handled"] = true;
            event.preventDefault();
            event.stopImmediatePropagation();
         }
      }

      public function A11yInitialFocus(items:Array) : void
      {
         var item:DisplayObject = null;
         items.sort(this.A11ySortFocusables);
         for each(item in items)
         {
            if(item.name.toLowerCase().indexOf("close") < 0)
            {
               this.A11yFocusItem(item);
               return;
            }
         }
         if(items.length > 0) { this.A11yFocusItem(items[0]); }
      }

      public function A11yPhonePage(direction:int) : Boolean
      {
         var node:DisplayObject = this.mA11yFocused;
         var paging:Object = null;
         var grid:Object = this.A11yFindScrollList(node);
         var page:int = 0;
         try
         {
            while(node != null)
            {
               if(getQualifiedClassName(node).indexOf("PhoneCategoryScreen") >= 0)
               {
                  paging = Object(node)["mcPaginationBar"]["PagingTarget"];
                  page = int(paging["CurrentPage"]) + direction;
                  if(page < 0 || page >= int(paging["PageCount"])) { return true; }
                  this.A11yFocusHover(this.mA11yFocused,null);
                  paging["AdvancePage"](direction);
                  this.mA11yList = null;
                  this.A11yRequestIndex(grid,direction > 0 ? 0 : int(this.A11yGridLayout(grid)["GetNumItems"]()) - 1,direction);
                  return true;
               }
               node = node.parent;
            }
         }
         catch(e:Error) { }
         return false;
      }

      public function A11yCalendarHeader(item:DisplayObject) : Boolean
      {
         return item != null && item.name == "txtHeaderTitle" && item.parent != null && "txtHeaderForecastName" in item.parent;
      }

      public function A11yCalendarAddOwner(item:DisplayObject) : DisplayObject
      {
         var depth:int = 0;
         try
         {
            // Returning from a dialog can restore its inner btnAdd. Keep
            // the localized row label attached to that same native action.
            while(item != null && depth < 6)
            {
               if(getQualifiedClassName(item).indexOf("widgets.Gameplay.Calendar.controls::ScheduleAdd") == 0 && "btnAdd" in item && "txtLabel" in item) { return item; }
               item = item.parent;
               depth = depth + 1;
            }
         }
         catch(e:Error) { }
         return null;
      }

      public function A11yTextDecoration(item:DisplayObject) : Boolean
      {
         try
         {
            if(item == null || item.parent == null) { return false; }
            // WorldCellView.Draw only fills pack captions for a locked world.
            // Its dormant authoring clips otherwise still contain Pack Name.
            if((item.name == "mcPackInfo" || item.name == "btnUnlock") && getQualifiedClassName(item.parent) == "widgets.GameEntry.WorldSelection.controls::WorldCellView" && "btnUnlock" in item.parent && Object(item.parent)["btnUnlock"] != null && !Object(item.parent)["btnUnlock"].visible) { return true; }
            // EA uses this clip as a layout anchor; the expander owns the
            // actual localized career/grade title, assigned by Draw().
            if(item.name == "mcJobTitle" && "mcJobInfoCellView" in item.parent) { return true; }
            // The noEmotion timeline retains authoring text such as Bored.
            // Keep a real career's ideal mood on the withEmotion timeline.
            if((item.name == "txtIdealMood" || item.name == "txtIdealMoodTitle") && getQualifiedClassName(item.parent).indexOf("CareerPanel::PerformanceMoodDetails") >= 0 && item.parent is MovieClip)
            {
               return MovieClip(item.parent).currentLabel == "noEmotion";
            }
         }
         catch(e:Error) { }
         return false;
      }

      public function A11yCalendarBusy(item:DisplayObject) : String
      {
         var day:Object = this.mA11yLastWidget;
         var names:Array = new Array();
         var id:String = null;
         var label:String = null;
         try
         {
            if(day == null || getQualifiedClassName(day).indexOf("CalendarDayView") < 0) { return ""; }
            var data:Object = day["TooltipExt"]["Data"];
            if(data == null) { return ""; }
            var keys:Object = getDefinitionByName("olympus.localization.Keys");
            var shifts:Object = data["GetWorkShifts"]();
            for(id in shifts)
            {
               label = keys["GENERIC_SIM_NAME"].toString({"simId":id});
               if(label != null && label.length > 0 && label != id && names.indexOf(label) < 0) { names.push(label); }
            }
            if(names.length > 0) { return Object(item)["txtHeader"].text + " " + names.join(", "); }
         }
         catch(e:Error) { }
         return "";
      }

      public function A11yCompleted(item:DisplayObject) : Boolean
      {
         try
         {
            if(item == null || getQualifiedClassName(item).indexOf("GoalCellView") < 0 && getQualifiedClassName(item).indexOf("ObjectiveCellView") < 0) { return false; }
            var check:DisplayObject = Object(item)["mcCheckMark"] as DisplayObject;
            if(check == null || !check.visible) { return false; }
            // Aspiration check marks use an empty "default" timeline frame.
            if(check is MovieClip && (MovieClip(check).currentLabel == "default" || MovieClip(check).currentLabel == "unchecked")) { return false; }
            return true;
         }
         catch(e:Error) { }
         return false;
      }

      public function A11yGridLayout(grid:Object) : Object
      {
         try
         {
            if(grid == null) { return null; }
            if("GetGridLayout" in grid) { return grid["GetGridLayout"](); }
            if("mGridLayout" in grid) { return grid["mGridLayout"]; }
         }
         catch(e:Error) { }
         return null;
      }

      public function A11yDialogCloseButton(item:DisplayObject) : Boolean
      {
         try
         {
            return item != null && item.name == "btnClose" && item.parent != null && getQualifiedClassName(item.parent).indexOf("widgets.Dialog.dialogs::") == 0;
         }
         catch(e:Error) { }
         return false;
      }

      public function A11yKeyboardDecoration(item:DisplayObject) : Boolean
      {
         if(this.A11yTextDecoration(item)) { return true; }
         var name:String = getQualifiedClassName(item);
         // Escape already closes the active screen. Keep the redundant
         // corner close button out of simplified option traversal.
         if(this.mA11ySimplifiedMenus && item.name == "btnClose" && this.A11ySimplifiedActive()) { return true; }
         // CAS: the category-list toggle tab reacts to synthetic hover and the
         // walker snapped back to the gallery button on every Tab (2026-09-16).
         if(name == "CharacterFilterTab" || item.name == "btnListToggle" && name.indexOf("Filter") >= 0) { return true; }
         // Neighborhood tags only show descriptive tooltips: EA deliberately
         // leaves StreetTag mouse press/release handlers empty. Their hover
         // artwork changes sorting order and traps Tab before the lot choices.
         // Houses remain focusable; these informational map markers do not.
         if(name == "widgets.GameEntry.Neighborhood.controls::StreetTag" || item.parent != null && "mcLots" in item.parent && "btnStreetTag" in item.parent && Object(item.parent)["btnStreetTag"] == item) { return true; }
         // Dialog "Close - ESC": Escape closes dialogs natively; the user rule
         // (2026-09-15) keeps it out of the Tab ring. Dialog containers only.
         if(this.A11yDialogCloseButton(item)) { return true; }
         if(this.mA11ySimplifiedMenus && this.A11ySimplifiedActive() && (item.name == "mcSaveListSlider" || item.name == "mcSlider" && item.parent != null && "mcScrollerView" in item.parent)) { return true; }
         if(item.parent != null && "txtHeaderForecastName" in item.parent && (item.name == "txtHeaderSubtitle" || item.name == "txtHeaderForecastName" || item.name == "txtFilterLabel")) { return true; }
         return item.name == "btnResize" || name.indexOf("InventoryPanel::SellButton") >= 0 || name.indexOf("Scrollbar") >= 0 || name.indexOf("ScrollBar") >= 0 || name.indexOf("Slider") >= 0 && (item.name.toLowerCase().indexOf("scroll") >= 0 || name.indexOf("Scroll") >= 0 || item.parent != null && (getQualifiedClassName(item.parent).indexOf("FilterPanel") >= 0 || "mScrollerView" in item.parent || "mcView" in item.parent || "mcScheduleView" in item.parent));
      }

      public function A11yCompositeRow(item:DisplayObject) : Boolean
      {
         if(item == null) { return false; }
         // Options categories are children of a ButtonBar, not one giant
         // button containing every category name.
         if(this.mA11ySimplifiedMenus && this.A11ySimplifiedActive() && getQualifiedClassName(item) == "scaleform.clik.controls::ButtonBar") { return true; }
         // Recipe rows wrap the real mcRowButton and an expandable serving
         // grid. Only the child button emits EA's mainRowClick event; focus
         // both it and visible serving buttons instead of the inert wrapper.
         if(getQualifiedClassName(item) == "widgets.Pickers.controls.GridPicker::RowCellView") { return true; }
         // EA's category cell wraps the world grid; StreetClip wraps mcLots.
         // Neither is the destination button. Stopping here hides its choices.
         if(getQualifiedClassName(item) == "widgets.GameEntry.WorldSelection.controls::WorldRegionTypeCellView" || getQualifiedClassName(item) == "widgets.GameEntry.Neighborhood.controls::StreetClip") { return true; }
         // Map movies give each street a linkage subclass (Street_SP, etc.).
         // Match the inherited public container fields, not its linkage name.
         if("mcLots" in item && "btnStreetTag" in item) { return true; }
         // MultiPickerCellView's picker content is protected. Its display
         // children remain traversable even though public-field probes fail.
         if(getQualifiedClassName(item) == "widgets.Pickers.controls.MultiPicker::MultiPickerCellView") { return true; }
         if("mcContent" in item && Object(item)["mcContent"] != null && "mcScrollList" in Object(item)["mcContent"]) { return true; }
         if(getQualifiedClassName(item) == "widgets.Gameplay.SimInfoHUD.CareerPanel::CareerCellView") { return true; }
         // A business employee group (current or available for hire) wraps
         // a grid of Sim cells; stopping on it read every name as one block.
         if(getQualifiedClassName(item) == "widgets.Gameplay.BusinessEmployeeManagement.controls::EmployeeGroupCellView") { return true; }
         // Category cells are containers, not individual skill/trait entries.
         if("mcScrollList" in item || "mcGoalGrid" in item || "mcTaskGrid" in item || "mcJobTitle" in item || "mcFilterSelection" in item || "mcFilterPanel" in item || "mcRoleSlotter" in item) { return true; }
         return getQualifiedClassName(item).indexOf("SummaryPanelContent") >= 0 || getQualifiedClassName(item).indexOf("PreferenceGroupCellView") >= 0 || "mcSkillGrid" in item || "mcTraitGrid" in item || "mcContentGrid" in item;
      }

      public function A11yWizardNavLabel(item:DisplayObject) : String
      {
         var layout:Object = null;
         var index:int = -1;
         var data:Object = null;
         try
         {
            if(item == null || getQualifiedClassName(item) != "widgets.Gameplay.SituationCreation.controls::WizardTopNavigationButton") { return ""; }
            layout = this.A11yGridLayout(this.A11yFindScrollList(item));
            if(layout == null || !("GetDataAtIndex" in layout) || !("GetCellIndexToDataIndex" in layout)) { return ""; }
            index = this.A11yCellIndexOf(layout,item);
            if(index < 0) { return ""; }
            // EA's cells and feed can have different indices. Read the native
            // MenuItem through its public layout API; Button has no data field.
            index = int(layout["GetCellIndexToDataIndex"](index));
            if(index < 0) { return ""; }
            data = layout["GetDataAtIndex"](index);
            if(data != null && "label" in data && data["label"] != null) { return String(data["label"]); }
         }
         catch(e:Error) { }
         return "";
      }

      public function A11yChoiceDescription(item:DisplayObject) : String
      {
         var row:DisplayObject = item;
         var name:String = "";
         var depth:int = 0;
         var layout:Object = null;
         var data:Object = null;
         var index:int = -1;
         var parts:Array = [];
         var value:String = "";
         var reward:String = "";
         var i:int = 0;
         var keys:Object = null;
         var careerConstants:Object = null;
         var branches:Array = null;
         var trades:Array = [];
         var agents:Array = null;
         var traits:Object = null;
         var trait:Object = null;
         var tradeKey:Object = null;
         var field:TextField = null;
         try
         {
            // Read the hovered/focused cell, never the previously selected
            // right panel. Reading must not activate or select a choice.
            while(row != null && depth < 14)
            {
               name = getQualifiedClassName(row);
               if(name == "widgets.Gameplay.SituationCreation.controls::SituationCellView" || name == "widgets.Gameplay.CareerSelector::TrackBlock") { break; }
               row = row.parent;
               depth++;
            }
            if(row == null || depth >= 14) { return ""; }
            layout = this.A11yGridLayout(this.A11yFindScrollList(row));
            if(layout == null || !("GetDataAtIndex" in layout) || !("GetCellIndexToDataIndex" in layout)) { return ""; }
            index = this.A11yCellIndexOf(layout,row);
            if(index < 0) { return ""; }
            // RecyclingGridLayout.GetGridIndexOfCell already maps the cell;
            // mapping twice loses descriptions once career rows scroll.
            if(getQualifiedClassName(layout) != "olympus.layout::RecyclingGridLayout" && getQualifiedClassName(layout) != "olympus.layout::SelectableRecyclingGridLayout") { index = int(layout["GetCellIndexToDataIndex"](index)); }
            if(index < 0) { return ""; }
            data = layout["GetDataAtIndex"](index);
            if(data == null) { return ""; }
            if(name == "widgets.Gameplay.SituationCreation.controls::SituationCellView")
            {
               if(data.icon_info == null) { return ""; }
               keys = getDefinitionByName("olympus.localization.KeysGP");
               if(data.isScoring)
               {
                  value = data.icon_info.GetMainObjective();
                  if(value != null && value.length > 0) { parts.push(keys.EVENT_CREATION_MAIN_OBJECTIVE.toString(value)); }
                  // Match SituationSelector's displayed reward tier/override.
                  if(data.challenge_reward_override != null && data.challenge_reward_override.length > 0)
                  {
                     for(i = 0; i < data.challenge_reward_override.length; i++) { reward = String(data.challenge_reward_override[i]); }
                  }
                  else if(data.rewards != null)
                  {
                     for(i = 0; i < data.rewards.length; i++) { reward = data.rewards[i].display_name.join(); }
                  }
                  if(reward.length > 0) { parts.push(keys.EVENT_CREATION_REWARD_LIST.toString(reward)); }
               }
               value = data.icon_info.GetLocationDesc();
               if(value != null && value.length > 0) { parts.push(keys.EVENT_CREATION_LOCATION_RESTRICTION.toString(value)); }
               value = data.icon_info.GetDesc();
               if(value != null && value.length > 0) { parts.push(value); }
            }
            else
            {
               if(data.description != null) { parts.push(data.description.toString({"simId":data.sim_id})); }
               keys = getDefinitionByName("olympus.localization.KeysGP");
               careerConstants = getDefinitionByName("gamedata.Gameplay.shared.definitions.CareerStaticData");
               if(data.career_panel_type == careerConstants.PANEL_TYPE_FREELANCE_CAREER)
               {
                  agents = data.currentCareerLevel.agents_available;
                  traits = getDefinitionByName("gamedata.Gameplay.shared.definitions.TraitsStaticData");
                  if(agents != null)
                  {
                     for(i = 0; i < agents.length; i++)
                     {
                        trait = traits.GetStaticData(agents[i]);
                        tradeKey = trait != null ? trait.GetTraitOriginDescriptionLocKeyBySimIdToken({"simId":data.sim_id}) : null;
                        if(tradeKey != null)
                        {
                           value = tradeKey.toString({"simId":data.sim_id});
                           if(trades.indexOf(value) < 0) { trades.push(value); }
                        }
                     }
                  }
                  if(trades.length > 0) { trades.sort(); parts.push(keys.CAREER_SELECTOR_TRADE_NAMES.toString() + trades.join(", ")); }
               }
               if(data.IsAgentRequired() && data.career_panel_type == careerConstants.PANEL_TYPE_AGENT_BASED_CAREER) { parts.push(keys.CAREER_SELECTOR_REQUIRES_AGENT.toString()); }
               else if(data.benefit_description != null && data.benefit_description.IsValid()) { parts.push(data.benefit_description.toString()); }
               else if(data.career_category == careerConstants.CATEGORY_WORK_FROM_HOME && data.work_from_home_description != null && data.work_from_home_description.IsValid()) { parts.push(data.work_from_home_description.toString({"simId":data.sim_id})); }
               branches = data.trackStaticData.branchesData;
               if(branches != null && branches.length == 2) { parts.push(keys.CAREER_SELECTOR_BRANCH_LIST.toString(keys.CAREER_SELECTOR_CAREER_BRANCHES.toString(),branches[0].name.toString({"simId":data.sim_id}),branches[1].name.toString({"simId":data.sim_id}))); }
            }
            field = new TextField();
            field.htmlText = parts.join("<br/> ");
            return field.text;
         }
         catch(e:Error) { }
         return "";
      }

      public function A11yMapLabel(item:DisplayObject) : String
      {
         var name:String = item != null ? getQualifiedClassName(item) : "";
         var data:Object = null;
         var label:String = "";
         try
         {
            // Use EA's public lot data, including localized custom lot names.
            // Keep the actual lot button and all native travel validation.
            if(item == null || !("GetData" in item) || !("lotId" in item)) { return ""; }
            if(name.indexOf("widgets.GameEntry.Neighborhood.controls::") != 0 && !("mcPositionHelper" in item && "mcMapTag" in item)) { return ""; }
            data = Object(item)["GetData"]();
            if(data == null || data.lotDescriptionData == null) { return ""; }
            label = data.lotDescriptionData.name.toString();
            if(data.venueData != null && data.venueData.Label != null && String(data.venueData.Label).length > 0) { label = label + ". " + String(data.venueData.Label); }
            return label;
         }
         catch(e:Error) { }
         return "";
      }

      // Picker rows whose selection is a native toggle: ObjectPicker*CellView
      // (olympus.gui.buttons.Button subclasses, public Selected) inside a
      // PickersMain dialog with EA's selectable layout. Autoaccept action
      // rows have Selected too, but are not checkboxes. Purchase rows keep
      // their quantity semantics.
      public function A11yPickerToggleCell(item:DisplayObject) : Boolean
      {
         var name:String = "";
         var layout:Object = null;
         var owner:DisplayObject = null;
         var hops:int = 0;
         try
         {
            if(item == null || !("Selected" in item)) { return false; }
            name = getQualifiedClassName(item);
            if(name.indexOf("widgets.Pickers.controls") != 0 || name.indexOf("Purchase") >= 0) { return false; }
            if(name.length < 8 || name.substr(name.length - 8) != "CellView") { return false; }
            layout = this.A11yGridLayout(this.A11yFindScrollList(item));
            if(layout == null || getQualifiedClassName(layout) != "olympus.layout::SelectableRecyclingGridLayout") { return false; }
            if(name.indexOf("ObjectPicker") < 0)
            {
               // SimPicker uses the selectable layout even for autoaccept.
               // Its native multi-select branch alone exposes btnDone.
               if(name != "widgets.Pickers.controls.SimPicker::DefaultSimPickerCellView" && name != "widgets.Pickers.controls.SimPicker::SimPickerCellView" && name != "widgets.Pickers.controls.SimPicker::SituationSimPickerCellView") { return false; }
               if(name == "widgets.Pickers.controls.SimPicker::SituationSimPickerCellView" && (!("mcHireSimControl" in item) || Object(item)["mcHireSimControl"] == null || Object(item)["mcHireSimControl"].visible)) { return false; }
               owner = item.parent;
               while(owner != null && hops < 14 && getQualifiedClassName(owner) != "widgets.Pickers.controls.SimPicker::SimPicker") { owner = owner.parent; hops++; }
               if(owner == null || !("btnDone" in owner) || !this.A11yIsLive(Object(owner)["btnDone"] as DisplayObject)) { return false; }
            }
            return this.A11yIsLive(this.mA11yActiveModalRoot) && getQualifiedClassName(this.mA11yActiveModalRoot).indexOf("PickersMain") >= 0;
         }
         catch(e:Error) { }
         return false;
      }

      public function A11ySaveChoice(item:DisplayObject) : Boolean
      {
         var name:String = "";
         var button:Object = null;
         try
         {
            if(item == null || !this.A11ySimplifiedActive()) { return false; }
            name = getQualifiedClassName(item);
            if(name != "widgets.General.SaveLoadMenu.controls::SaveSlotDetailed" && name != "widgets.General.SaveLoadMenu.controls::SaveSlotLite") { return false; }
            button = Object(item)["btnPlay"];
            // Native metadata distinguishes Load Game from Save As without
            // matching a translated label or changing save-file contents.
            return button != null && button.visible && button["AudioExt"]["ElementName"] == "LoadGame";
         }
         catch(e:Error) { }
         return false;
      }

      public function A11yConfirmSinglePicker(item:DisplayObject) : Boolean
      {
         var owner:DisplayObject = item;
         var root:Object = this.mA11yActiveModalRoot;
         var button:DisplayObject = null;
         try
         {
            if(!this.A11ySimplifiedActive() || !this.A11yIsLive(item) || !this.A11yPickerToggleCell(item)) { return false; }
            if(Object(item)["Selected"] != true || root == null || !("A11ySingleSelection" in root) || !root["A11ySingleSelection"]()) { return false; }
            while(owner != null && owner != this.mTooltipsLayer.stage)
            {
               if("btnDone" in owner)
               {
                  button = Object(owner)["btnDone"] as DisplayObject;
                  if(this.A11yClickControl(button)) { return true; }
               }
               owner = owner.parent;
            }
         }
         catch(e:Error) { }
         return false;
      }

      public function A11ySelectionCount(item:DisplayObject) : String
      {
         var layout:Object = null;
         var feed:Object = null;
         try
         {
            if(!this.A11ySimplifiedActive() || !this.A11yPickerToggleCell(item)) { return ""; }
            layout = this.A11yGridLayout(this.A11yFindScrollList(item));
            if(layout == null || !("GetDataFeed" in layout)) { return ""; }
            feed = layout["GetDataFeed"]();
            if(feed != null && "GetSelectedIndices" in feed) { return String(feed["GetSelectedIndices"]().length) + " selected"; }
         }
         catch(e:Error) { }
         return "";
      }

      public function A11yActionProxy(item:DisplayObject) : DisplayObject
      {
         if(item == null) { return null; }
         if(this.mA11ySimplifiedMenus && this.A11ySaveChoice(item)) { return Object(item)["btnPlay"] as DisplayObject; }
         if(item.parent != null && "mcFilterBubble" in item.parent && Object(item.parent)["mcFilterBubble"] == item) { return Object(item.parent)["btnFilterPanel"] as DisplayObject; }
         if("btnSolve" in item) { return Object(item)["btnSolve"] as DisplayObject; }
         if("btnAdd" in item && "txtLabel" in item) { return Object(item)["btnAdd"] as DisplayObject; }
         // Event planner role slots: the cell text is the label, mcPickSims is the
         // PushButton whose CLICK requests EA's Sim picker (RoleSlotCellView).
         if("mcPickSims" in item && getQualifiedClassName(item).indexOf("SituationCreation.controls::RoleSlotCellView") >= 0) { return Object(item)["mcPickSims"] as DisplayObject; }
         if("btnCellView" in item) { return Object(item)["btnCellView"] as DisplayObject; }
         if("btnDropdown" in item && getQualifiedClassName(item).indexOf("MultipickerDropdownCellView") >= 0) { return Object(item)["btnDropdown"] as DisplayObject; }
         return item;
      }

      public function A11yHoverProxy(item:DisplayObject) : DisplayObject
      {
         if(item != null && "btnCellView" in item) { return Object(item)["btnCellView"] as DisplayObject; }
         return item;
      }

      public function A11yGridStep(direction:int, vertical:Boolean) : Boolean
      {
         var grid:Object = this.A11yFindScrollList(this.mA11yFocused);
         var layout:Object = this.A11yGridLayout(grid);
         var dimensions:Array = null;
         var columns:int = 1;
         var index:int = -1;
         var target:int = -1;
         var count:int = 0;
         var coordinates:Array = null;
         var nextCoordinates:Array = null;
         try
         {
            if(layout == null) { return false; }
            index = grid == this.mA11yLogicalList ? this.mA11yLogicalIndex : this.A11yCellIndexOf(layout,this.mA11yFocused);
            if(index < 0) { return false; }
            if(this.A11yCompositeRow(layout["GetViewAtIndex"](index))) { return false; }
            dimensions = layout["GetGridDimensions"]();
            columns = Math.max(1,int(dimensions[0]));
            count = int(layout["GetNumItems"]());
            if(columns == 1 || int(dimensions[1]) == 1)
            {
               // One-dimensional lists retain both arrow pairs for walking.
               target = index + direction;
            }
            else
            {
               target = index + direction * (layout["Horizontal"] ? (vertical ? columns : 1) : (vertical ? 1 : int(dimensions[1])));
               if(target >= 0 && target < count)
               {
                  coordinates = layout["IndexToGridCoord"](index);
                  nextCoordinates = layout["IndexToGridCoord"](target);
                  if(int(coordinates[vertical ? 0 : 1]) != int(nextCoordinates[vertical ? 0 : 1])) { return true; }
               }
            }
            if(target < 0 || target >= count) { if(!vertical) { this.A11yPhonePage(direction); } return true; }
            return this.A11yRequestIndex(grid,target,direction);
         }
         catch(e:Error) { }
         return false;
      }

      public function A11yGroupOwner(item:DisplayObject) : Object
      {
         var node:DisplayObject = item;
         var name:String = null;
         while(node != null && node != this.mA11yScope)
         {
            name = getQualifiedClassName(node);
            if(name.indexOf("Filter") >= 0 && node is DisplayObjectContainer && name.indexOf("Button") < 0 && name.indexOf("Cell") < 0) { return node; }
            if(name.indexOf("Calendar.controls::Schedule") >= 0 && name.indexOf("Entry") >= 0) { return node; }
            node = node.parent;
         }
         var grid:Object = this.A11yFindScrollList(item);
         return grid != null ? grid : item;
      }

      public function A11yGroupArrow(direction:int) : Boolean
      {
         var owner:Object = this.A11yGroupOwner(this.mA11yFocused);
         var items:Array = new Array();
         var index:int = -1;
         // A filter row is a Tab group, but arrows must cross rows in the
         // open filter popup instead of cycling one checkbox forever.
         if(this.mA11yScope != null && getQualifiedClassName(this.mA11yScope).indexOf("FilterPanel") >= 0) { owner = this.mA11yScope; }
         if(owner == null || owner == this.mA11yFocused && getQualifiedClassName(owner).indexOf("Calendar.controls::Schedule") < 0) { return false; }
         this.A11yCollectFocusables(owner as DisplayObject,items,0);
         items.sort(this.A11ySortFocusables);
         index = items.indexOf(this.mA11yFocused);
         if(index < 0 || items.length < 2) { return false; }
         this.A11yFocusItem(items[(index + direction + items.length) % items.length]);
         return true;
      }

      public function A11yFindScrollList(param1:DisplayObject) : Object
      {
         var _loc2_:DisplayObject = param1;
         var _loc3_:int = 0;
         var _loc4_:Object = null;
         while(_loc2_ != null && _loc3_ < 14)
         {
            try
            {
               _loc4_ = _loc2_;
               if(this.A11yGridLayout(_loc4_) != null)
               {
                  return _loc4_;
               }
            }
            catch(e:Error)
            {
            }
            _loc2_ = _loc2_.parent;
            _loc3_++;
         }
         return null;
      }

      public function A11yCellIndexOf(param1:Object, param2:DisplayObject) : int
      {
         var _loc3_:DisplayObject = param2;
         var _loc4_:int = 0;
         var _loc5_:int = 0;
         while(_loc3_ != null && _loc4_ < 14)
         {
            try
            {
               _loc5_ = int(param1["GetGridIndexOfCell"](_loc3_));
               if(param1["GetViewAtIndex"](_loc5_) == _loc3_)
               {
                  return _loc5_;
               }
            }
            catch(e:Error)
            {
            }
            _loc3_ = _loc3_.parent;
            _loc4_++;
         }
         return -1;
      }

      protected var mA11yIdxInList:Boolean = false;

      // row pitch of the pending index-scroll, for A11yIndexFrame's
      // progressive nudge (see there)
      protected var mA11yIdxPitch:Number = 0;

      public function A11yStepInList(param1:int) : Boolean
      {
         try { return this.A11yIndexScroll(param1,false); }
         catch(e:Error) { }
         return false;
      }

      public function A11yIndexScroll(param1:int, param2:Boolean = true) : Boolean
      {
         var list:Object = null;
         var layout:Object = null;
         var index:int = -1;
         var count:int = 0;
         var target:int = 0;
         try
         {
            list = this.A11yFindScrollList(this.mA11yFocused);
            if(list == null) { return false; }
            layout = this.A11yGridLayout(list);
            index = list == this.mA11yLogicalList ? this.mA11yLogicalIndex : this.A11yCellIndexOf(layout,this.mA11yFocused);
            count = int(layout["GetNumItems"]());
            if(index < 0 || count == 0) { return false; }
            target = index + param1;
            if(target < 0 || target >= count)
            {
               if(!param2) { return false; }
               target = (target + count) % count;
            }
            return this.A11yRequestIndex(list,target,param1);
         }
         catch(e:Error) { }
         return false;
      }

      public function A11yRequestIndex(list:Object, target:int, direction:int) : Boolean
      {
         var cell:DisplayObject = null;
         try
         {
            this.mA11yIdxLayout = this.A11yGridLayout(list);
            this.mA11yIdxList = list;
            this.mA11yIdxTarget = target;
            this.mA11yIdxDir = direction;
            this.mA11yIdxTries = 0;
            cell = this.A11yRevealIndex();
            if(cell != null)
            {
               this.mA11yIdxDir = 0;
               this.A11yFocusCell(cell);
               return true;
            }
            this.mTooltipsLayer.addEventListener(Event.ENTER_FRAME,this.A11yIndexFrame,false,0,true);
            return true;
         }
         catch(e:Error) { this.A11yCancelIndex(); }
         return false;
      }

      public function A11yFocusCell(cell:DisplayObject) : void
      {
         var items:Array = new Array();
         try
         {
            this.A11yCollectFocusables(cell,items,0);
            this.mA11yList = null;
            this.A11yFocusItem(items.length > 0 ? items[0] : cell);
         }
         catch(e:Error) { }
      }

      // Work in the scroller's coordinates, so UI scaling does not alter
      // slider distances. For recycled offscreen cells, estimate from a
      // live anchor in the same layout; then recheck the actual bounds.
      public function A11yRevealIndex() : DisplayObject
      {
         var layout:Object = this.mA11yIdxLayout;
         var list:Object = this.mA11yIdxList;
         var scroller:DisplayObjectContainer = null;
         var maskObject:DisplayObject = null;
         var viewport:Rectangle = null;
         var bounds:Rectangle = null;
         var cell:DisplayObject = null;
         var anchor:DisplayObject = null;
         var other:DisplayObject = null;
         var cells:Object = null;
         var dimensions:Array = null;
         var columns:int = 1;
         var anchorIndex:int = -1;
         var otherIndex:int = -1;
         var rowDelta:int = 0;
         var i:int = 0;
         var pitch:Number = 0;
         var delta:Number = 0;
         var value:Number = 0;
         var desired:Number = 0;
         var slider:Object = null;
         try
         {
            if(list == null || !this.A11yIsLive(list as DisplayObject)) { return null; }
            cell = layout["GetViewAtIndex"](this.mA11yIdxTarget) as DisplayObject;
            if(!("mScrollerView" in list))
            {
               if(this.A11yIsLive(cell)) { this.A11yRevealControl(cell); return cell; }
               return null;
            }
            scroller = list["mScrollerView"] as DisplayObjectContainer;
            if(scroller == null) { return null; }
            maskObject = Object(scroller)["mcMask"] as DisplayObject;
            if(maskObject == null) { return null; }
            viewport = maskObject.getBounds(scroller);
            if(viewport.height <= 0) { return null; }
            cell = layout["GetViewAtIndex"](this.mA11yIdxTarget) as DisplayObject;
            if(cell != null && this.A11yIsLive(cell))
            {
               bounds = cell.getBounds(scroller);
            }
            else
            {
               dimensions = layout["GetGridDimensions"]();
               columns = Math.max(1,int(dimensions[layout["Horizontal"] ? 0 : 1]));
               cells = layout["GetAllDisplayObjectCells"]();
               for each(other in cells)
               {
                  if(this.A11yIsLive(other)) { anchor = other; break; }
               }
               if(anchor == null) { return null; }
               anchorIndex = this.A11yCellIndexOf(layout,anchor);
               if(anchorIndex < 0) { return null; }
               bounds = anchor.getBounds(scroller);
               pitch = Number(layout["GetCellBounds"]().height) + Number(layout["GetCellPadding"]().Vertical);
               for each(other in cells)
               {
                  otherIndex = this.A11yCellIndexOf(layout,other);
                  rowDelta = int(otherIndex / columns) - int(anchorIndex / columns);
                  if(otherIndex >= 0 && rowDelta != 0 && this.A11yIsLive(other))
                  {
                     delta = (other.getBounds(scroller).top - bounds.top) / rowDelta;
                     if(delta > 0) { pitch = delta; break; }
                  }
               }
               if(isNaN(pitch) || pitch <= 0) { return null; }
               bounds.y = bounds.y + (int(this.mA11yIdxTarget / columns) - int(anchorIndex / columns)) * pitch;
               cell = null;
            }
            delta = 0;
            if(bounds.height > viewport.height || bounds.top < viewport.top) { delta = bounds.top - viewport.top; }
            else if(bounds.bottom > viewport.bottom) { delta = bounds.bottom - viewport.bottom; }
            slider = list["mSlider"];
            value = Number(slider["Value"]);
            desired = Math.max(Number(slider["MinValue"]),Math.min(Number(slider["MaxValue"]),value + delta));
            if(Math.abs(desired - value) > 0.5)
            {
               slider["SetCurrentValue"](desired,false,true,true);
               return null;
            }
            if(cell != null && this.A11yCellIndexOf(layout,cell) == this.mA11yIdxTarget && bounds.intersects(viewport)) { return cell; }
         }
         catch(e:Error) { }
         return null;
      }

      public function A11yIndexFrame(param1:Event) : void
      {
         var cell:DisplayObject = null;
         try
         {
            this.mA11yIdxTries = this.mA11yIdxTries + 1;
            cell = this.A11yRevealIndex();
            if(cell == null && this.mA11yIdxTries < 30) { return; }
            this.mTooltipsLayer.removeEventListener(Event.ENTER_FRAME,this.A11yIndexFrame);
            this.mA11yIdxDir = 0;
            if(cell == null)
            {
               this.A11yPostToPython("a11y.mark","picker-reveal-failed-" + this.mA11yIdxTarget);
               this.mA11yNavQueue.length = 0;
               return;
            }
            this.A11yFocusCell(cell);
            this.A11yDrainNav();
         }
         catch(e:Error) { this.A11yCancelIndex(); }
      }

      public function A11yArrowNav(param1:int) : void
      {
         var _loc2_:Stage = null;
         var _loc3_:String = null;
         try
         {
            this.A11yModalFrame();
            if(this.mA11yPendingScope != null || this.mA11yIdxDir != 0)
            {
               this.mA11yNavQueue.push(param1 * 5);
               return;
            }
            if(this.mA11yScope == null || this.mA11yScope.stage == null)
            {
               return;
            }
            _loc3_ = getQualifiedClassName(this.mA11yScope);
            if(!this.A11yIsModalScope(this.mA11yScope))
            {
               return;
            }
            _loc2_ = this.mTooltipsLayer != null ? this.mTooltipsLayer.stage : null;
            if(_loc2_ != null && _loc2_.focus is TextField)
            {
               return;
            }
            if(this.mA11ySimplifiedMenus && this.A11ySimplifiedActive()) { this.A11yTabMove(param1); return; }
            if(this.A11yCalendarStep(param1,true)) { return; }
            if(this.A11yGridStep(param1,true)) { return; }
            if(this.A11yGroupArrow(param1)) { return; }
            this.A11yTabMove(param1);
         }
         catch(e:Error)
         {
         }
      }

      public function A11yMsgArrowUp(param1:Object = null) : void
      {
         this.A11yArrowNav(-1);
      }

      public function A11yMsgArrowDown(param1:Object = null) : void
      {
         this.A11yArrowNav(1);
      }

      public function A11yMsgArrowLeft(param1:Object = null) : void
      {
         this.A11yArrowHorizontal(-1);
      }

      public function A11yMsgArrowRight(param1:Object = null) : void
      {
         this.A11yArrowHorizontal(1);
      }

      // A quantity row (the purchase picker's cells) exposes IncreaseAmount
      // and DecreaseAmount. Found by DUCK TYPING up the parent chain, never
      // by importing PurchasePickerCellView: that class lives only in the
      // PickersPurchase movie, and a static reference to a class a movie
      // does not contain is resolved when the AVM VERIFIES the method,
      // before any try/catch inside it can run: an uncatchable native
      // crash (the CAS lesson). A missing property just throws here, which
      // the catch absorbs.
      public function A11yFindStepper(param1:DisplayObject) : Object
      {
         var _loc2_:DisplayObject = param1;
         var _loc3_:int = 0;
         var _loc4_:Object = null;
         while(_loc2_ != null && _loc3_ < 6)
         {
            try
            {
               _loc4_ = _loc2_;
               if(_loc4_["IncreaseAmount"] is Function && _loc4_["DecreaseAmount"] is Function)
               {
                  return _loc4_;
               }
            }
            catch(e:Error)
            {
            }
            _loc2_ = _loc2_.parent;
            _loc3_++;
         }
         return null;
      }

      // Left/Right on a quantity row adjust that row instead of moving
      // focus, the standard spinbutton convention: Up/Down walk the list,
      // Left/Right change the value under you. Everywhere else Left/Right
      // keep their old meaning (move focus), so other pickers and dialogs
      // are unaffected. The row's own Increase/DecreaseAmount are called,
      // which is the same funnel the mouse uses, so the quantity and
      // totals announcements come along for free.
      public function A11yArrowHorizontal(param1:int) : void
      {
         var _loc2_:Object = null;
         var _loc3_:Stage = null;
         var _loc4_:String = null;
         try
         {
            this.A11yModalFrame();
            // Quantity changes follow pending movement to the intended row.
            if(this.mA11yPendingScope != null || this.mA11yIdxDir != 0)
            {
               this.mA11yNavQueue.push(param1 * 2);
               return;
            }
            if(this.mA11yScope == null || this.mA11yScope.stage == null)
            {
               return;
            }
            _loc4_ = getQualifiedClassName(this.mA11yScope);
            if(!this.A11yIsModalScope(this.mA11yScope))
            {
               return;
            }
            _loc3_ = this.mTooltipsLayer != null ? this.mTooltipsLayer.stage : null;
            if(_loc3_ != null && _loc3_.focus is TextField)
            {
               return;
            }
            _loc2_ = this.A11yFindStepper(this.mA11yFocused);
            if(this.A11yCalendarStep(param1,false)) { return; }
            if(_loc2_ != null)
            {
               if(param1 > 0)
               {
                  _loc2_["IncreaseAmount"]();
               }
               else
               {
                  _loc2_["DecreaseAmount"]();
               }
               return;
            }
            if(this.A11yGridStep(param1,false)) { return; }
            if(this.A11yGroupArrow(param1)) { return; }
            this.A11yTabMove(param1);
         }
         catch(e:Error)
         {
         }
      }

      public function A11yTryScrollUnused() : void
      {
      }

      public function A11yDrawFocusRing(param1:DisplayObject) : void
      {
         var _loc2_:Rectangle = null;
         try
         {
            if(this.mA11yRing == null)
            {
               this.mA11yRing = new Sprite();
               this.mA11yRing.mouseEnabled = false;
            }
            _loc2_ = this.A11ySeasonBounds(param1);
            if(this.A11yCalendarHeader(param1))
            {
               _loc2_ = _loc2_.union(DisplayObject(Object(param1.parent)["txtHeaderSubtitle"]).getBounds(param1.stage));
               _loc2_ = _loc2_.union(DisplayObject(Object(param1.parent)["txtHeaderForecastName"]).getBounds(param1.stage));
            }
            if(param1.parent != null && "mcFilterBubble" in param1.parent && Object(param1.parent)["mcFilterBubble"] == param1)
            {
               _loc2_ = _loc2_.union(DisplayObject(Object(param1.parent)["btnFilterPanel"]).getBounds(param1.stage));
            }
            if(this.mA11yRingBounds != null && this.mA11yRingBounds.equals(_loc2_) && this.mA11yRing.parent != null) { return; }
            this.mA11yRingBounds = _loc2_.clone();
            this.mA11yRing.graphics.clear();
            this.mA11yRing.graphics.lineStyle(3,16776960,1);
            this.mA11yRing.graphics.drawRect(_loc2_.x,_loc2_.y,_loc2_.width,_loc2_.height);
            if(this.mTooltipsLayer != null)
            {
               this.mTooltipsLayer.addChild(this.mA11yRing);
            }
         }
         catch(e:Error)
         {
         }
      }

      public function A11yOnStageClick(param1:MouseEvent) : void
      {
         var _loc2_:String = null;
         var target:DisplayObject = null;
         try
         {
            if(this.mA11yActivating)
            {
               return;
            }
            this.mA11yPointerSpeechHeld = false;
            if(this.mA11yFocused == null && this.mA11yScope == null)
            {
               return;
            }
            if(this.mA11yScope != null)
            {
               _loc2_ = getQualifiedClassName(this.mA11yScope);
               if(this.A11yIsModalScope(this.mA11yScope))
               {
                  this.A11yCancelIndex();
                  this.mA11yList = null;
                  target = this.A11yFindWidget(param1.target as DisplayObject);
                  if(target != null && this.mA11yScope is DisplayObjectContainer && DisplayObjectContainer(this.mA11yScope).contains(target))
                  {
                     this.A11yFocusItem(target);
                     this.mA11yPointerSpeechHeld = false;
                  }
                  return;
               }
            }
            this.A11yClearFocus();
         }
         catch(e:Error)
         {
         }
      }

      public function A11yClearFocus() : void
      {
         try
         {
            this.A11yFocusHover(this.mA11yFocused,null);
            this.A11yWatchFocused(this.mA11yFocused,null);
            this.A11yCancelIndex();
            this.mA11yFocused = null;
            if(!this.A11yIsModalScope(this.mA11yScope)) { this.mA11yScope = null; }
            this.mA11yPendingScope = null;
            this.mA11yFocusPending = null;
            this.mA11yNavQueue.length = 0;
            if(this.mTooltipsLayer != null) { this.mTooltipsLayer.removeEventListener(Event.ENTER_FRAME,this.A11yScopeFrame); }
            this.mA11yList = null;
            this.mA11yListRoot = null;
            this.A11yClearRing();
         }
         catch(e:Error)
         {
         }
      }

      public function A11yClearRing() : void
      {
         try
         {
            if(this.mA11yRing != null)
            {
               this.mA11yRing.graphics.clear();
               if(this.mA11yRing.parent != null)
               {
                  this.mA11yRing.parent.removeChild(this.mA11yRing);
               }
            }
         }
         catch(e:Error)
         {
         }
      }

      // Diagnostic only (2026-09-24): per-target geometry for the inspect dump,
      // so hidden-but-live controls (CAS GameTray leftovers) can be rejected on
      // evidence. Never throws; returns "" on any failure.
      public function A11yInspectGeometry(item:DisplayObject) : String
      {
         var r:Rectangle = null;
         var node:DisplayObject = null;
         var clipped:String = "";
         var under:Array = null;
         var top:DisplayObject = null;
         var covered:String = "?";
         var onstage:String = "?";
         try
         {
            if(item == null || item.stage == null) { return "nostage"; }
            r = item.getBounds(item.stage);
            onstage = (r.right > 0 && r.bottom > 0 && r.left < item.stage.stageWidth && r.top < item.stage.stageHeight) ? "1" : "0";
            node = item;
            while(node != null)
            {
               if(node.mask != null) { clipped = clipped + "mask@" + node.name + ";"; }
               if(node.scrollRect != null) { clipped = clipped + "scrollRect@" + node.name + ";"; }
               node = node.parent;
            }
            under = item.stage.getObjectsUnderPoint(new Point(r.left + r.width / 2, r.top + r.height / 2));
            if(under != null && under.length > 0)
            {
               top = under[under.length - 1] as DisplayObject;
               covered = (top == item || (top != null && item is DisplayObjectContainer && DisplayObjectContainer(item).contains(top))) ? "0" : "1:" + getQualifiedClassName(top) + "/" + (top != null ? top.name : "");
            }
            else { covered = "none"; }
            return "bounds=" + Math.round(r.left) + "," + Math.round(r.top) + "," + Math.round(r.width) + "x" + Math.round(r.height) + " onstage=" + onstage + " alpha=" + item.alpha + " covered=" + covered + (clipped != "" ? " clip=" + clipped : "");
         }
         catch(e:Error) { }
         return "";
      }

      public function A11yInspect(param1:Object = null) : void
      {
         var lines:Array = new Array();
         var node:DisplayObject = this.mA11yFocused;
         var items:Array = new Array();
         var child:DisplayObject = null;
         var depth:int = 0;
         var index:int = 0;
         try
         {
            while(node != null && depth < 10)
            {
               lines.push("ancestor " + depth + " " + getQualifiedClassName(node) + "/" + node.name);
               if(depth == 0 && node is DisplayObjectContainer)
               {
                  while(index < DisplayObjectContainer(node).numChildren && index < 30)
                  {
                     child = DisplayObjectContainer(node).getChildAt(index);
                     lines.push("child " + getQualifiedClassName(child) + "/" + child.name + " visible=" + child.visible + " semantic=" + (this.A11ySemanticTarget(child) == child));
                     index = index + 1;
                  }
               }
               node = node.parent;
               depth = depth + 1;
            }
            if(this.mA11yScope != null)
            {
               lines.push("scope " + getQualifiedClassName(this.mA11yScope) + "/" + this.mA11yScope.name);
               this.A11yCollectFocusables(this.mA11yScope,items,0);
               items.sort(this.A11ySortFocusables);
               index = 0;
               while(index < items.length && index < 60)
               {
                  child = items[index];
                  lines.push("target " + index + " " + getQualifiedClassName(child) + "/" + child.name + " " + this.A11yInspectGeometry(child));
                  index = index + 1;
               }
            }
            this.A11yPostToPython("a11y.inspect_enc",encodeURIComponent(lines.join("\n")));
         }
         catch(e:Error) { this.A11yPostToPython("a11y.inspect_enc",encodeURIComponent("inspect error " + e.message)); }
      }

      public function A11yWatchFocused(param1:DisplayObject, param2:DisplayObject) : void
      {
         try
         {
            if(param1 != null)
            {
               param1.removeEventListener(Event.REMOVED_FROM_STAGE,this.A11yOnFocusedRemoved);
            }
            if(param2 != null)
            {
               param2.addEventListener(Event.REMOVED_FROM_STAGE,this.A11yOnFocusedRemoved,false,0,true);
            }
         }
         catch(e:Error)
         {
         }
      }

      public function A11yOnFocusedRemoved(param1:Event) : void
      {
         try
         {
            if(param1.target != this.mA11yFocused)
            {
               return;
            }
            this.A11yWatchFocused(this.mA11yFocused,null);
            this.mA11yFocused = null;
            this.mA11yList = null;
            this.A11yClearRing();
            // Keep the old scope until A11yModalFrame restores its parent.
            this.mA11yListRoot = null;
         }
         catch(e:Error)
         {
         }
      }

      public function A11ySafeDispatch(param1:DisplayObject, param2:String) : void
      {
         try
         {
            param1.dispatchEvent(this.A11yMouseEx(param2));
         }
         catch(e:Error)
         {
         }
      }

      public function A11yMouseEx(param1:String) : MouseEvent
      {
         var _loc2_:MouseEventEx = null;
         try
         {
            _loc2_ = new MouseEventEx(param1);
            _loc2_.buttonIdx = MouseEventEx.LEFT_BUTTON;
            return _loc2_;
         }
         catch(e:Error)
         {
         }
         return new MouseEvent(param1,true,false);
      }

      // A focused control can stay on the stage while the thing behind it
      // is already torn down. The purchase picker nulls its dialog message
      // on reset/close, so activating its Done button during teardown blew
      // up inside EA's SendCommand (#1009, reported 2026-08-10 with a
      // loading screen active). A mouse user cannot click in that window;
      // the keyboard can. Require the whole parent chain to still be
      // visible before firing a synthetic click.
      public function A11yIsLive(param1:DisplayObject) : Boolean
      {
         var current:DisplayObject = param1;
         try
         {
            if(current == null || current.stage == null) { return false; }
            while(current != null)
            {
               if(!current.visible || current.alpha <= 0.01) { return false; }
               current = current.parent;
            }
            return true;
         }
         catch(e:Error) { }
         return false;
      }


      public function A11yClickControl(target:DisplayObject) : Boolean
      {
         try
         {
            if(!this.A11yIsLive(target)) { return false; }
            if("enabled" in target && Object(target)["enabled"] == false) { return false; }
            if("mouseEnabled" in target && Object(target)["mouseEnabled"] == false) { return false; }
            this.mA11yActivating = true;
            this.A11ySafeDispatch(target,MouseEvent.MOUSE_DOWN);
            this.A11ySafeDispatch(target,MouseEvent.MOUSE_UP);
            this.A11ySafeDispatch(target,MouseEvent.CLICK);
            this.mA11yActivating = false;
            return true;
         }
         catch(e:Error) { this.mA11yActivating = false; }
         return false;
      }

      public function A11yActivate(confirm:Boolean = true) : void
      {
         var _loc1_:Rectangle = null;
         var _loc2_:DisplayObject = null;
         try
         {
            this.A11yModalFrame();
            if(this.mA11yIdxDir != 0) { this.mA11yNavQueue.push(confirm ? 0 : 4); return; }
            if(this.mA11yPendingScope != null) { this.mA11yNavQueue.push(confirm ? 0 : 4); return; }
            if(!this.mA11yKeyboard) { return; }
            _loc2_ = this.mA11yFocused;
            if(this.A11ySeasonActivate(_loc2_,confirm)) { return; }
            if(this.A11yActivateCASName(_loc2_)) { return; }
            if(_loc2_ is TextField)
            {
               if(TextField(_loc2_).type == "input") { _loc2_.stage.focus = TextField(_loc2_); }
               else { this.A11yAnnounceDisplay(_loc2_,"a11y.focus_enc",true); }
               return;
            }
            if(_loc2_ != null && this.A11yActionProxy(_loc2_) == _loc2_ && (("enabled" in _loc2_ && Object(_loc2_)["enabled"] == false) || ("mouseEnabled" in _loc2_ && Object(_loc2_)["mouseEnabled"] == false)))
            {
               this.A11yAnnounceDisplay(_loc2_,"a11y.widget_enc",true);
               return;
            }
            if(_loc2_ == null)
            {
               return;
            }
            if(_loc2_.stage == null)
            {
               return;
            }
            if(!this.A11yIsLive(_loc2_))
            {
               this.A11yClearFocus();
               return;
            }
            if(this.A11yActionProxy(_loc2_) != _loc2_)
            {
               // A disabled proxied control (a child's calendar Add Event) used to
               // fail silently; the narrator translates this token. Ordinary
               // disabled controls still read EA's own reason.
               if(!this.A11yClickControl(this.A11yActionProxy(_loc2_))) { this.A11yPostToPython("a11y.widget_enc",encodeURIComponent("0|0|action unavailable")); }
               return;
            }
            if(this.A11yInformational(_loc2_) && !this.A11yIsFocusable(_loc2_)) { this.A11yAnnounceDisplay(_loc2_,"a11y.focus_enc",true); return; }
            if(confirm && getQualifiedClassName(_loc2_).indexOf("PurchasePickerCellView") >= 0 && this.A11yPickerFooter(_loc2_)) { return; }
            if(confirm && this.A11yInventoryMenu(_loc2_)) { return; }
            this.mA11yActivating = true;
            this.A11ySafeDispatch(_loc2_,MouseEvent.MOUSE_DOWN);
            this.A11ySafeDispatch(_loc2_,MouseEvent.MOUSE_UP);
            this.A11ySafeDispatch(_loc2_,MouseEvent.CLICK);
            // A toggled picker row reads its new state through the existing
            // settled reread (no new listener); EA applies the toggle this frame.
            if(this.A11yPickerToggleCell(_loc2_)) { this.mA11yFocusPending = _loc2_; this.mA11yFocusDue = getTimer() + 150; }
            this.mA11yActivating = false;
            this.mA11yList = null;
            if(confirm && this.mA11ySimplifiedMenus && this.A11yConfirmSinglePicker(_loc2_)) { this.mA11yFocusPending = null; return; }
            if(confirm && this.A11yIsLive(_loc2_) && getQualifiedClassName(_loc2_).indexOf("SituationCellView") >= 0) { this.A11yPickerFooter(_loc2_,true); }
            if(confirm && getQualifiedClassName(_loc2_).indexOf("CalendarDayView") >= 0) { this.A11yCalendarSchedule(); }
         }
         catch(e:Error)
         {
            this.mA11yActivating = false;
         }
      }

      public function A11yMsgNext(param1:Object = null) : void
      {
         this.A11yModalFrame();
         // A queued menu key must not fall back to the whole stage after close.
         if(!this.A11yIsModalScope(this.mA11yScope) && !this.A11yIsModalScope(this.mA11yPendingScope)) { return; }
         this.A11yTabMove(1);
      }

      public function A11yMsgPrev(param1:Object = null) : void
      {
         this.A11yModalFrame();
         // A queued menu key must not fall back to the whole stage after close.
         if(!this.A11yIsModalScope(this.mA11yScope) && !this.A11yIsModalScope(this.mA11yPendingScope)) { return; }
         this.A11yTabMove(-1);
      }

      public function A11yMsgActivate(param1:Object = null) : void
      {
         this.A11yActivate();
      }

      public function A11yMsgClear(param1:Object = null) : void
      {
         this.A11yClearFocus();
      }

      public function A11yMsgAutoFocusOn(param1:Object = null) : void
      {
         this.mA11yAutoFocus = true;
      }

      public function A11yMsgAutoFocusOff(param1:Object = null) : void
      {
         this.mA11yAutoFocus = false;
      }

      public function A11yOnKeyDown(param1:KeyboardEvent) : void
      {
         try
         {
            if(param1.target is TextField)
            {
               return;
            }
            if(param1.keyCode == 9)
            {
               param1.stopImmediatePropagation();
               param1.preventDefault();
               this.A11yTabMove(param1.shiftKey ? -1 : 1);
            }
            else if(param1.keyCode == 221 || param1.keyCode == 39 && param1.ctrlKey)
            {
               param1.stopImmediatePropagation();
               param1.preventDefault();
               this.A11yTabMove(1);
            }
            else if(param1.keyCode == 219 || param1.keyCode == 37 && param1.ctrlKey)
            {
               param1.stopImmediatePropagation();
               param1.preventDefault();
               this.A11yTabMove(-1);
            }
            else if(param1.keyCode == 13)
            {
               if(this.mA11yFocused != null)
               {
                  param1.stopPropagation();
                  this.A11yActivate();
               }
            }
            else if(param1.keyCode == 27)
            {
               this.A11yClearFocus();
            }
         }
         catch(e:Error)
         {
         }
      }

      public function A11yCheckboxState(param1:DisplayObject) : String
      {
         var _loc2_:String = null;
         var _loc3_:DisplayObjectContainer = null;
         var _loc4_:int = 0;
         var _loc5_:* = undefined;
         try
         {
            if(this.A11ySingleFilterLabel(param1) == param1 && param1 != null)
            {
               return this.A11yCheckboxState(Object(param1.parent)["btnCheckBox"]);
            }
            _loc2_ = getQualifiedClassName(param1);
            if(this.A11yPickerToggleCell(param1))
            {
               return Object(param1)["Selected"] == true ? "checked" : "unchecked";
            }
            if(_loc2_.indexOf("Checkbox") >= 0)
            {
               _loc5_ = param1;
               if(_loc5_.Selected == true)
               {
                  return "checked";
               }
               return "unchecked";
            }
            _loc3_ = param1 as DisplayObjectContainer;
            if(_loc3_ != null)
            {
               _loc4_ = 0;
               while(_loc4_ < _loc3_.numChildren)
               {
                  _loc2_ = this.A11yCheckboxState(_loc3_.getChildAt(_loc4_));
                  if(_loc2_.length > 0)
                  {
                     return _loc2_;
                  }
                  _loc4_++;
               }
            }
         }
         catch(e:Error)
         {
         }
         return "";
      }

      public function A11yHoldPointerSpeech() : void
      {
         try
         {
            this.mA11yPointerSpeechHeld = this.A11ySimplifiedActive() && this.mTooltipsLayer != null && this.mTooltipsLayer.stage != null;
            if(this.mA11yPointerSpeechHeld)
            {
               this.mA11yPointerSpeechX = this.mTooltipsLayer.stage.mouseX;
               this.mA11yPointerSpeechY = this.mTooltipsLayer.stage.mouseY;
            }
         }
         catch(e:Error) { this.mA11yPointerSpeechHeld = false; }
      }

      public function A11yIgnoreStationaryHover() : Boolean
      {
         try
         {
            if(!this.mA11yPointerSpeechHeld || !this.mA11yKeyboard || !this.A11ySimplifiedActive() || !this.A11yIsLive(this.mA11yFocused)) { return false; }
            var stage:Stage = this.mTooltipsLayer.stage;
            if(stage != null && Math.abs(stage.mouseX - this.mA11yPointerSpeechX) <= 1 && Math.abs(stage.mouseY - this.mA11yPointerSpeechY) <= 1) { return true; }
         }
         catch(e:Error) { }
         this.mA11yPointerSpeechHeld = false;
         return false;
      }

      public function A11yOnMouseOver(param1:MouseEvent) : void
      {
         if(this.mA11ySyntheticHover) { return; }
         // Recycling or revealing rows can cause real rollover events under
         // a stationary pointer. They must not interrupt keyboard selection.
         // Moving or clicking the pointer restores ordinary hover narration.
         if(this.A11yIgnoreStationaryHover()) { return; }
         var _loc2_:DisplayObject = null;
         var _loc3_:DisplayObject = null;
         try
         {
            _loc2_ = param1.target as DisplayObject;
            if(_loc2_ == null)
            {
               return;
            }
            if(this.A11yFundsTarget(_loc2_)) { return; }
            if(this.mTooltipsLayer != null && this.mTooltipsLayer.contains(_loc2_))
            {
               return;
            }
            _loc3_ = this.A11yFindWidget(_loc2_);
            if(_loc3_ != null) { _loc3_ = this.A11ySemanticTarget(_loc3_); }
            if(_loc3_ == null && _loc2_ is TextField)
            {
               _loc3_ = this.A11yGroupText(_loc2_);
            }
            if(_loc3_ == null)
            {
               return;
            }
            if(_loc3_ == this.mA11yLastWidget)
            {
               return;
            }
            this.mA11yLastWidget = _loc3_;
            if(getQualifiedClassName(_loc3_).indexOf("CatalogImageCellView") >= 0 || getQualifiedClassName(_loc3_).indexOf("ProductCatalogCellView") >= 0)
            {
               return;
            }
            this.A11yAnnounceDisplay(_loc3_,"a11y.widget_enc",false);
         }
         catch(e:Error)
         {
         }
      }

      public static function getInstance() : TooltipManager
      {
         return sInstance;
      }

      public function Disable(param1:Boolean = true) : void
      {
         this.mbDisabled = param1;
         if(param1)
         {
            this.HideTooltips(true);
         }
      }

      public function Clear() : void
      {
         var _loc1_:String = null;
         this.A11yResetGameState();
         this.HideTooltips(true);
         for(_loc1_ in this.mTooltips)
         {
            delete this.mTooltips[_loc1_];
         }
         this.mTooltipsLayer.Clear();
      }

      public function GetTooltip(param1:Class) : ITooltip
      {
         var _loc3_:String = null;
         var _loc2_:ITooltip = null;
         if(!param1 || param1 == Tooltip)
         {
            _loc2_ = this.mDefaultTooltip;
         }
         else
         {
            _loc3_ = getQualifiedClassName(param1);
            _loc2_ = this.mTooltips[_loc3_];
            if(_loc2_ == null)
            {
               _loc2_ = new param1() as ITooltip;
               if(_loc2_ != null)
               {
                  this.mTooltips[_loc3_] = _loc2_;
               }
               else
               {
                  _loc2_ = this.mDefaultTooltip;
               }
            }
         }
         return _loc2_;
      }

      public function ShowTooltip(param1:ITooltip, param2:int) : void
      {
         if(this.mbDisabled)
         {
            return;
         }
         if(param1 != null)
         {
            param1.Show(param2);
            this.A11yAnnounceDisplay(param1 as DisplayObject,"a11y.speak_enc");
         }
      }

      public function A11yEffectiveAlpha(param1:DisplayObject) : Number
      {
         var _loc2_:Number = 1;
         var _loc3_:DisplayObject = param1;
         var _loc4_:int = 0;
         while(_loc3_ != null && _loc4_ < 10)
         {
            if(!_loc3_.visible)
            {
               return 0;
            }
            _loc2_ = _loc2_ * _loc3_.alpha;
            if(_loc2_ < 0.05)
            {
               return _loc2_;
            }
            _loc3_ = _loc3_.parent;
            _loc4_++;
         }
         return _loc2_;
      }

      public function A11yHiddenHireControl(item:DisplayObject) : Boolean
      {
         return item != null && !item.visible && item.parent != null && getQualifiedClassName(item.parent) == "widgets.Pickers.controls.SimPicker::SituationSimPickerCellView" && "mcHireSimControl" in item.parent && Object(item.parent)["mcHireSimControl"] == item;
      }

      public function A11yCollectText(param1:DisplayObject, param2:Array, param3:int = 0, param4:Boolean = true) : void
      {
         var _loc4_:TextField = null;
         var _loc5_:DisplayObjectContainer = null;
         var _loc6_:int = 0;
         var _loc7_:Point = null;
         var _loc8_:String = null;
         if(param2.length > 24)
         {
            return;
         }
         if(this.A11yTextDecoration(param1) || this.A11yHiddenHireControl(param1)) { return; }
         _loc4_ = param1 as TextField;
         if(_loc4_ != null)
         {
            if(_loc4_.name == "txtNewContent")
            {
               return;
            }
            if(_loc4_.visible && _loc4_.text != null && _loc4_.text.length > 0)
            {
               _loc7_ = _loc4_.localToGlobal(new Point(0,0));
               param2.push(int(_loc7_.y).toString() + "|" + int(_loc7_.x).toString() + "|" + this.A11yTextValue(_loc4_));
            }
            return;
         }
         _loc5_ = param1 as DisplayObjectContainer;
         if(_loc5_ != null)
         {
            // Panels the game keeps built but hidden (fame reputation, clubs,
            // empty stat rows) hold visible TextFields inside a hidden
            // container, so prune the whole subtree. Depth 0 is the tooltip
            // root itself, which is never pruned: it can still be mid
            // show-transition when we announce. NEVER test alpha here:
            // tooltips fade in from alpha 0 and that silences everything.
            // param4=false skips the pruning entirely: hovered/focused ROW
            // announcements fire the instant the pointer lands, when legit
            // sub-containers (paged or freshly recycled list rows) can still
            // report visible=false and pruning silenced the skill rows'
            // "title, then level" read (2026-08-02). Composed tooltips and
            // the Sim headline keep pruning; that is where the phantom
            // hidden-panel text lived.
            if(param4 && param3 > 0 && !_loc5_.visible)
            {
               return;
            }
            _loc8_ = getQualifiedClassName(param1);
            if(_loc8_.indexOf("CalendarCareerTooltipEntry") >= 0)
            {
               var busy:String = this.A11yCalendarBusy(param1);
               if(busy.length > 0)
               {
                  _loc7_ = param1.localToGlobal(new Point(0,0));
                  param2.push(int(_loc7_.y).toString() + "|" + int(_loc7_.x).toString() + "|" + busy);
               }
               return;
            }
            if(_loc8_.indexOf("Badge") >= 0 || _loc8_.indexOf("NewItemsClip") >= 0)
            {
               return;
            }
            _loc6_ = 0;
            while(_loc6_ < _loc5_.numChildren)
            {
               this.A11yCollectText(_loc5_.getChildAt(_loc6_),param2,param3 + 1,param4);
               _loc6_++;
            }
         }
      }

      // A stack-count badge caption and nothing else: "x" + digits.
      public function A11yIsBareCount(param1:String) : Boolean
      {
         var _loc2_:int = 0;
         if(param1 == null || param1.length < 2 || param1.length > 7)
         {
            return false;
         }
         if(param1.charAt(0) != "x")
         {
            return false;
         }
         _loc2_ = 1;
         while(_loc2_ < param1.length)
         {
            if(param1.charCodeAt(_loc2_) < 48 || param1.charCodeAt(_loc2_) > 57)
            {
               return false;
            }
            _loc2_++;
         }
         return true;
      }

      public function A11yFirstPersonState() : Boolean
      {
         var active:Boolean = false;
         try
         {
            if(this.mA11yStartupActive || this.A11yWorldHudMode() != 1)
            {
               this.mA11yFirstPersonKnown = false;
               return false;
            }
            active = Boolean(CommunicationManager.CallGameService("IsUsingCameraControllerFPS",null));
            if(this.mA11yFirstPersonKnown && active != this.mA11yFirstPerson)
            {
               this.mA11yFirstPersonFence = getTimer() + 350;
               this.A11yPostToPython("a11y.speak_enc",encodeURIComponent("0|0|" + (active ? "First-person camera on." : "First-person camera off.")));
            }
            this.mA11yFirstPersonKnown = true;
            this.mA11yFirstPerson = active;
         }
         catch(e:Error) { }
         return active;
      }

      public function A11yNextStartupPort(port:int) : int
      {
         return port == 45993 ? 45995 : (port == 45995 ? 45994 : 45993);
      }

      public function A11ySimplifiedActive() : Boolean
      {
         // CAS and Stories are explicitly outside this feature. Keep their
         // existing field, part, questionnaire and name-entry navigation.
         if(!this.mA11ySimplifiedMenus || this.A11yGameState() == 983016380) { return false; }
         if(this.A11yCASStoryScope() != null) { return false; }
         if(this.mA11yScope != null && getQualifiedClassName(this.mA11yScope).indexOf("widgets.CAS.") == 0) { return false; }
         return true;
      }

      public function A11ySetSimplifiedMenus(enabled:Boolean) : void
      {
         if(this.mA11ySimplifiedMenus == enabled) { return; }
         this.mA11ySimplifiedMenus = enabled;
         this.A11yCancelIndex();
         this.mA11yNavQueue.length = 0;
         this.mA11yList = null;
         this.A11yFenceOpeningInput();
      }

      public function A11yOptionPosition(item:DisplayObject) : String
      {
         var list:Object = null;
         var layout:Object = null;
         var items:Array = new Array();
         var index:int = -1;
         var count:int = 0;
         try
         {
            if(!this.A11ySimplifiedActive() || item == null || item != this.mA11yFocused) { return ""; }
            list = this.A11yFindScrollList(item);
            if(list != null)
            {
               layout = this.A11yGridLayout(list);
               index = this.A11yCellIndexOf(layout,item);
               count = int(layout["GetNumItems"]());
            }
            else if(this.mA11yScope != null)
            {
               this.A11yCollectFocusables(this.mA11yScope,items,0);
               items.sort(this.A11ySortFocusables);
               index = items.indexOf(item);
               count = items.length;
            }
            if(index >= 0 && index < count) { return String(index + 1) + " of " + String(count); }
         }
         catch(e:Error) { }
         return "";
      }

      public function A11yAnnounceDisplay(param1:DisplayObject, param6:String = "a11y.speak_enc", param7:Boolean = true) : void
      {
         var _loc2_:Array = null;
         var _loc3_:String = null;
         var _loc4_:String = null;
         var _loc5_:int = 0;
         var _loc7_:String = null;
         var _loc8_:String = null;
         var _loc9_:String = null;
         var _loc10_:int = 0;
         try
         {
            if(param1 == null)
            {
               return;
            }
            if(this.mA11yOpening) { return; }
            if(param6 == "a11y.widget_enc" || param6 == "a11y.focus_enc")
            {
               var calendarAdd:DisplayObject = this.A11yCalendarAddOwner(param1);
               if(calendarAdd != null) { param1 = calendarAdd; }
            }
            if((param6 == "a11y.widget_enc" || param6 == "a11y.focus_enc") && ("btnCellView" in param1 || getQualifiedClassName(param1).indexOf("InventoryCellViewButton") >= 0)) { return; }
            if((param6 == "a11y.widget_enc" || param6 == "a11y.focus_enc") && this.A11yFundsTarget(param1)) { return; }
            if(param6 == "a11y.speak_enc" && param1 == this.mDefaultTooltip && "txtField" in param1 && String(Object(param1)["txtField"].text) == this.mA11ySilentMood) { return; }
            _loc2_ = new Array();
            this.A11yCollectText(param1,_loc2_,0,param7);
            if(this.mA11ySimplifiedMenus && this.A11ySaveChoice(param1))
            {
               _loc2_ = new Array();
               this.A11yCollectText(Object(param1)["txtSaveName"] as DisplayObject,_loc2_,0,param7);
               this.A11yCollectText(Object(param1)["txtHouseholdName"] as DisplayObject,_loc2_,0,param7);
               this.A11yCollectText(Object(param1)["txtTimestamp"] as DisplayObject,_loc2_,0,param7);
               if("txtRequiresPackLabel" in param1) { this.A11yCollectText(Object(param1)["txtRequiresPackLabel"] as DisplayObject,_loc2_,0,param7); }
               if("txtRestartRequiredLabel" in param1) { this.A11yCollectText(Object(param1)["txtRestartRequiredLabel"] as DisplayObject,_loc2_,0,param7); }
            }
            if(param6 == "a11y.widget_enc" || param6 == "a11y.focus_enc") { this.A11yRentalQuote(param1,_loc2_); this.A11yMoveInQuote(param1,_loc2_); this.A11yTransferQuote(param1,_loc2_); this.A11yMoveLabel(param1,_loc2_); this.A11yOptionsRowLabel(param1,_loc2_); }
            _loc7_ = this.A11yMapLabel(param1);
            if(_loc7_.length > 0) { _loc2_ = ["0|0|" + _loc7_]; }
            if("A11yMotiveText" in param1) { _loc2_ = ["0|0|" + Object(param1)["A11yMotiveText"]()]; }
            if(this.A11yCalendarHeader(param1))
            {
               var forecast:TextField = Object(param1.parent)["txtHeaderForecastName"] as TextField;
               _loc2_ = ["0|0|" + TextField(param1).text + ". " + TextField(Object(param1.parent)["txtHeaderSubtitle"]).text + (forecast != null && forecast.visible ? ". " + forecast.text : "")];
            }
            if(this.A11yCompleted(param1)) { _loc2_.push("999999|0|Completed"); }
            _loc7_ = this.A11yCalendarLabel(param1);
            if(_loc7_.length > 0) { _loc2_ = ["-999999|0|" + _loc7_]; }
            if((param6 == "a11y.widget_enc" || param6 == "a11y.focus_enc"))
            {
               try
               {
                  if("TooltipExt" in param1 && Object(param1)["TooltipExt"]["Text"] != null)
                  {
                     _loc7_ = String(Object(param1)["TooltipExt"]["Text"]);
                     if(_loc7_.length > 0) { _loc2_.push("999998|999998|" + _loc7_); }
                  }
               }
               catch(tooltipError:Error) { }
            }
            // Prefer EA's localized tooltip; add a fallback only when neither
            // visible text nor the native tooltip supplies a label.
            if(_loc2_.length == 0 && getQualifiedClassName(param1).indexOf("PhoneButton") >= 0) { _loc2_ = ["0|0|phone"]; }
            if(_loc2_.length == 0) { _loc7_ = this.A11yWizardNavLabel(param1); if(_loc7_.length > 0) { _loc2_ = ["0|0|" + _loc7_]; } }
            if((param6 == "a11y.widget_enc" || param6 == "a11y.focus_enc"))
            {
               _loc7_ = this.A11yChoiceDescription(param1);
               if(_loc7_.length > 0) { _loc2_.push("999999|999998|" + _loc7_); }
               _loc7_ = this.A11yCheckboxState(param1);
               if(_loc7_.length > 0)
               {
                  _loc2_.push("999999|999999|" + _loc7_);
               }
            }
            if((param6 == "a11y.widget_enc" || param6 == "a11y.focus_enc") && _loc2_.length == 1)
            {
               // Stack-count badges ("x2"; also EA's INVISIBLE
               // authoring placeholders that read "x99" over unstacked
               // household inventory cells) never announce alone: the
               // count is folded into the cell's composed line
               // (CatalogImageCellView), and a bare badge line landing
               // inside the tooltip delay used to CANCEL the pending
               // item description (2026-08-20). Return without the
               // widgetname/stop fallback so a parked description
               // survives untouched.
               _loc9_ = String(_loc2_[0]);
               _loc10_ = _loc9_.lastIndexOf("|");
               if(this.A11yIsBareCount(_loc9_.substr(_loc10_ + 1)))
               {
                  return;
               }
            }
            if(this.mA11ySimplifiedMenus && (param6 == "a11y.widget_enc" || param6 == "a11y.focus_enc") && _loc2_.length > 0)
            {
               _loc7_ = this.A11yOptionPosition(param1);
               if(_loc7_.length > 0) { _loc2_.push("999999|999999|" + _loc7_); }
               _loc7_ = this.A11ySelectionCount(param1);
               if(_loc7_.length > 0) { _loc2_.push("999999|999999|" + _loc7_); }
            }
            _loc3_ = _loc2_.join("\u0001");
            if(_loc3_ == null || _loc3_.length == 0)
            {
               if(param6 == "a11y.focus_enc") { return; }
               if((param6 == "a11y.widget_enc" || param6 == "a11y.focus_enc"))
               {
                  _loc8_ = param1.name;
                  if(_loc8_ != null && _loc8_.length > 2 && _loc8_.indexOf("instance") != 0)
                  {
                     if(_loc8_.indexOf("btn") == 0)
                     {
                        _loc8_ = _loc8_.substr(3);
                     }
                     else if(_loc8_.indexOf("mc") == 0)
                     {
                        _loc8_ = _loc8_.substr(2);
                     }
                     this.A11yPostToPython("a11y.widgetname_enc",encodeURIComponent(_loc8_));
                  }
                  else
                  {
                     this.A11yPostToPython("a11y.stop","1");
                  }
               }
               return;
            }
            _loc5_ = getTimer();
            if(_loc3_ == this.mA11yLast && _loc5_ - this.mA11yLastTime < 1500)
            {
               return;
            }
            if(_loc5_ - this.mA11yWindowStart > 1000)
            {
               this.mA11yWindowStart = _loc5_;
               this.mA11yWindowCount = 0;
            }
            this.mA11yWindowCount++;
            if(this.mA11yWindowCount > 20 && param6 != "a11y.focus_enc")
            {
               return;
            }
            this.mA11yLast = _loc3_;
            this.mA11yLastTime = _loc5_;
            if(_loc3_.length > 1400)
            {
               _loc3_ = _loc3_.substr(0,1400);
            }
            if(!this.mA11yMarked)
            {
               // Only consider the mark delivered once a zone exists; before
               // that PostServerCommand silently goes nowhere and setting the
               // flag first burned it for the whole session (fixed
               // 2026-08-03). Announcing at all means the UI is live, but the
               // very first announce can still precede the command channel,
               // so re-arm until a payload has actually been sent.
               if(this.mA11ySentAny)
               {
                  this.mA11yMarked = true;
               }
               this.A11yPostToPython("a11y.mark","A11YLIBNAME");
            }
            this.mA11ySentAny = true;
            _loc4_ = encodeURIComponent(_loc3_);
            _loc4_ = _loc4_.split("'").join("%27");
            _loc4_ = _loc4_.split("(").join("%28");
            _loc4_ = _loc4_.split(")").join("%29");
            _loc4_ = _loc4_.split("!").join("%21");
            _loc4_ = _loc4_.split("~").join("%7E");
            _loc4_ = _loc4_.split("*").join("%2A");
            this.A11yPostToPython(param6,_loc4_);
         }
         catch(e:Error)
         {
         }
      }

      public function HideTooltip(param1:ITooltip, param2:Boolean = false, param3:int = 500) : void
      {
         if(param1 != null)
         {
            param1.Hide(param2,param3);
         }
      }

      public function HideTooltips(param1:Boolean = false) : void
      {
         var _loc2_:ITooltip = null;
         this.HideTooltip(this.mDefaultTooltip,param1);
         for each(_loc2_ in this.mTooltips)
         {
            if(_loc2_ != null)
            {
               this.HideTooltip(_loc2_,param1);
            }
         }
      }

      public function AddTooltip(param1:DisplayObject) : void
      {
         if(this.mbDisabled)
         {
            return;
         }
         if(!this.mTooltipsLayer.contains(param1))
         {
            this.mTooltipsLayer.addChild(param1);
         }
         this.A11yTryHookStage();
         param1.addEventListener(Event.ENTER_FRAME,this.A11yOnTooltipFrame,false,0,true);
      }

      public function IsTooltipShown(param1:DisplayObject) : Boolean
      {
         return this.mTooltipsLayer.contains(param1);
      }

      public function RemoveTooltip(param1:DisplayObject) : void
      {
         if(this.mTooltipsLayer.contains(param1))
         {
            this.mTooltipsLayer.removeChild(param1);
         }
      }
   }
}
