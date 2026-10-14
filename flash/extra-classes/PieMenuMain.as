package widgets.Gameplay.PieMenu
{
   import flash.events.FocusEvent;
   import flash.events.MouseEvent;
   import flash.geom.Point;
   import flash.ui.Keyboard;
   import gamedata.Gameplay.InteractionMenu.InteractionCategory;
   import gamedata.Gameplay.InteractionMenu.InteractionMenuData;
   import gamedata.Gameplay.InteractionMenu.InteractionMenuItem;
   import gamedata.Gameplay.Persistence.GameSaveLockUnlock;
   import gamedata.Gameplay.PieMenu.PieMenuButtonData;
   import gamedata.Gameplay.shared.GameplayStateData;
   import gamedata.Gameplay.shared.WorldPickResult;
   import gamedata.TutorialTip.TutorialMode;
   import gamedata.shared.FlyAwayText;
   import olympus.constants.GameStateFlags;
   import olympus.constants.InputActionPriorities;
   import olympus.constants.VirtualCursorConstants;
   import olympus.core.Ticker;
   import olympus.core.widget.WidgetBase;
   import olympus.events.PushButtonEvent;
   import olympus.events.TickerEvent;
   import olympus.extensions.TooltipExtension;
   import olympus.gamepad.EnterParams;
   import olympus.gamepad.LayoutAPI;
   import olympus.gamepad.NavDirection;
   import olympus.gamepad.NavManager;
   import olympus.gui.buttons.Button;
   import olympus.input.IInputFocusable;
   import olympus.input.InputAction;
   import olympus.input.InputTrigger;
   import olympus.input.adapters.DynamicOmnidirectionalAdapter;
   import olympus.core.TooltipManager;
   import olympus.io.CommunicationManager;
   import olympus.io.DebugCommands;
   import olympus.io.InputActionManager;
   import olympus.localization.KeysGE;
   import olympus.localization.KeysGP;
   import olympus.localization.LocKey;
   import olympus.objects.SimPB;
   import olympus.utils.DisplayObjectUtils;
   import olympus.utils.InputUtils;
   import olympus.utils.MovieClipUtils;
   import olympus.utils.SystemUtils;
   import scaleform.gfx.MouseEventEx;
   import widgets.Gameplay.PieMenu.constants.PieMenuConstants;
   import widgets.Gameplay.PieMenu.constants.PieMenuTunables;
   import widgets.Gameplay.events.*;
   import widgets.Gameplay.gamepad.adapters.GameplayCenterDragAdapter;
   
   public class PieMenuMain extends WidgetBase
   {
      
      public var mcMenu:PieMenuBase;
      
      protected var mPickResults:WorldPickResult = new WorldPickResult();
      
      protected var mLastInteractionRequestId:uint;
      
      protected var mMenuData:InteractionMenuData;
      
      protected var isCloseEvent:Boolean;
      
      protected var isInventoryRequest:Boolean;
      
      protected var itemPosition:Point;
      
      public var btnTravel:Button;
      
      protected var mRoot:InteractionCategory;
      
      protected var mInputActionExit:InputAction;
      
      protected var mInputActionHideTravelBtn:InputAction;
      
      protected var mbSocialMenuDisabled:Boolean;
      
      protected var mbForceDisableTravelBtn:Boolean = false;
      
      protected var mbShiftOnPickup:Boolean = false;
      
      internal var mInputAdapter:DynamicOmnidirectionalAdapter;
      
      public static const A11Y_REF_OBJECT:uint = 2703146145;
      
      public static const A11Y_REF_SIM:uint = 2703146146;
      
      public function PieMenuMain()
      {
         super();
         mbShouldAddToControllerSimulatedStack = true;
      }
      
      override public function Initialize() : void
      {
         super.Initialize();
         Telemetry.EnableVisibilityTelemetry = false;
         with(this.mcMenu)
         {
            visible = false;
            addEventListener(PieMenuEvent.OPTION_SELECTED,OnOptionSelected,false,0,true);
            addEventListener(PieMenuEvent.MENU_CANCELLED,OnMenuCancelled,false,0,true);
            AddMessageListener("OpenPieMenuWithObjectId",OnOpenPieMenu);
         }
         AddMessageListener("PieMenuCreate",this.HandlePieMenuCreate,InteractionMenuData);
         AddMessageListener("SimActivated",this.HandleSimChanged);
         AddMessageListener("SimDeactivated",this.HandleSimChanged);
         AddMessageListener("WorldPickDownEvent",this.HandleWorldPickDown);
         AddMessageListener("WorldPickUpEvent",this.HandleWorldPickUp);
         AddMessageListener("GameplayOptionsChanged",this.HandleOptionsValueChanged);
         AddMessageListener("ForceDisableTravelBtn",this.HandleForceDisableTravelBtn);
         AddMessageListener("SituationStart",this.HandleSituationStart);
         AddMessageListener("SituationEnded",this.HandleSituationEnd);
         CommunicationManager.RegisterServiceHandler("ToggleTravelButton",this.HandleToggleTravelButton,this);
         DebugCommands.Register("ui.qa.close_interaction_menu",this.DebugCommandCloseInteractionMenu,"","Closes the interaction menu.");
         this.btnTravel.visible = false;
         this.btnTravel.addEventListener(PushButtonEvent.CLICK,this.OnTravelButtonClicked,false,0,true);
         MovieClipUtils.DisableMouseScrollOnClip(this);
         this.mbSocialMenuDisabled = CommunicationManager.CallGameService("OptionsGetValue",{"name":"TradSocialMenuEnabled"});
         this.mInputActionExit = InputAction.WhenTriggered(InputTrigger.FromKeyBinding(Keyboard.ESCAPE)).CallFunction(this.HandleEscapeKey).SetPriority(InputActionPriorities.ESC_PIE_MENU);
         this.mInputActionHideTravelBtn = InputAction.WhenTriggered(InputTrigger.FromKeyBinding(Keyboard.ESCAPE)).CallFunction(this.HandleHideTravelBtn).SetPriority(InputActionPriorities.ESC_PIE_MENU);
         if(SystemUtils.UsingConsoleInputMode)
         {
            this.InitGamepad();
         }
         AddMessageListener("A11yOpenPieMenu",this.A11yOnOpenPieMenu);
      }
      
      override public function Unload() : void
      {
         if(this.mcMenu.visible)
         {
            CommunicationManager.SendMessage("HidePieMenu",null);
         }
         super.Unload();
         Ticker.Remove(this.btnTravel);
         InputActionManager.UnregisterAction(this.mInputActionExit);
         InputActionManager.UnregisterAction(this.mInputActionHideTravelBtn);
         DebugCommands.Unregister("ui.qa.close_interaction_menu");
         DebugCommands.Unregister("ui.toggle_pie_menu_visualizer");
         DebugCommands.Unregister("ui.debug_social_front_page");
         CommunicationManager.RemoveMessageListener("PieMenuCreate",this.HandlePieMenuCreate,this);
         stage.removeEventListener(FocusEvent.MOUSE_FOCUS_CHANGE,this.OnFocusChange);
         stage.removeEventListener(MouseEvent.CLICK,this.OnStageMouseClick);
         stage.removeEventListener(MouseEvent.MOUSE_DOWN,this.OnMouseDownOnStage);
         stage.removeEventListener(FocusEvent.MOUSE_FOCUS_CHANGE,this.OnTravelBtnFocusChange);
         stage.removeEventListener(MouseEvent.CLICK,this.OnTravelBtnStageMouseClick);
         stage.removeEventListener(MouseEvent.MOUSE_DOWN,this.OnTravelBtnMouseDownOnStage);
      }
      
      override public function Hide(param1:Object = null) : void
      {
         try
         {
            CommunicationManager.PostServerCommand("a11y.menuclosed","1");
         }
         catch(e:Error)
         {
         }
         this.mcMenu.visible = false;
         this.mcMenu.CloseCurrentMenu();
         stage.focus = null;
         InputActionManager.UnregisterAction(this.mInputActionExit);
         stage.removeEventListener(FocusEvent.MOUSE_FOCUS_CHANGE,this.OnFocusChange);
         stage.removeEventListener(MouseEvent.CLICK,this.OnStageMouseClick);
         stage.removeEventListener(MouseEvent.MOUSE_DOWN,this.OnMouseDownOnStage);
         if(this.mMenuData)
         {
            mAudioExtension.DispatchHide();
         }
         CommunicationManager.RemoveMessageListener("SetModalVisible",this.HandleSetModalVisible,this);
         CommunicationManager.SendUIMessage("ClosePieMenu",param1);
         if(SystemUtils.UsingController)
         {
            NavManager.Instance.TryFocusBack(this.mInputAdapter);
            this.mInputAdapter.SetContainer(null);
         }
         if(SystemUtils.UsingMouseKeyboard)
         {
            NavManager.Instance.RemoveFromControllerSimulatedStack(mName);
         }
      }
      
      override public function Show(param1:Object = null) : void
      {
         if(SystemUtils.UsingController && NavManager.Instance.CurrentWidgetName != WidgetName)
         {
            NavManager.Instance.FocusWidgetForward(WidgetName);
         }
         if(SystemUtils.UsingMouseKeyboard)
         {
            NavManager.Instance.AddToControllerSimulatedStack(mName);
         }
         this.mcMenu.visible = true;
         this.HandleToggleTravelButton(false);
         CommunicationManager.AddMessageListener("SetModalVisible",this.HandleSetModalVisible,this);
         mAudioExtension.DispatchShow();
         InputActionManager.RegisterAction(this.mInputActionExit);
         stage.addEventListener(FocusEvent.MOUSE_FOCUS_CHANGE,this.OnFocusChange,false,0,true);
         stage.addEventListener(MouseEvent.CLICK,this.OnStageMouseClick,false,0,true);
         stage.addEventListener(MouseEvent.MOUSE_DOWN,this.OnMouseDownOnStage,false,0,true);
      }
      
      protected function HandleSimChanged(param1:Object) : void
      {
         if(this.mcMenu.visible)
         {
            CommunicationManager.SendMessage("HidePieMenu",null);
         }
         if(this.btnTravel.visible)
         {
            this.HandleToggleTravelButton(true);
         }
      }
      
      protected function HandleWorldPickDown(param1:Object) : void
      {
         var _loc2_:WorldPickResult = new WorldPickResult(param1);
         if(this.mcMenu.visible && _loc2_.pickType != PieMenuConstants.PICK_OBJECT && _loc2_.pickType != PieMenuConstants.PICK_SIM)
         {
            this.isCloseEvent = true;
            CommunicationManager.SendMessage("HidePieMenu",null);
            return;
         }
         if(this.mcMenu.visible)
         {
            CommunicationManager.SendMessage("HidePieMenu",null);
         }
         else
         {
            this.isCloseEvent = false;
         }
         this.mPickResults = _loc2_;
      }
      
      protected function HandleWorldPickUp(param1:Object) : void
      {
         if(!this.mPickResults)
         {
            return;
         }
         if(this.isCloseEvent)
         {
            this.isCloseEvent = false;
            return;
         }
         var _loc2_:int = int(param1["modControl"]);
         var _loc3_:int = int(param1["modAlt"]);
         var _loc4_:int = param1["modShift"] as int;
         _loc4_ = _loc4_ << 1 & 2;
         this.mbShiftOnPickup = _loc4_ != 0;
         var _loc5_:uint = ++this.mLastInteractionRequestId;
         if(_loc5_ == 0)
         {
            _loc5_ = ++this.mLastInteractionRequestId;
         }
         this.isInventoryRequest = false;
         CommunicationManager.CallGameService("PostServerCommand",{
            "command":"interactions.choices",
            "commandArgs":[this.mPickResults.objectId,this.mPickResults.pickType,this.mPickResults.worldPosX,this.mPickResults.worldPosY,this.mPickResults.worldPosZ,this.mPickResults.lotId,this.mPickResults.level,_loc2_,_loc3_,_loc4_,_loc5_,0,0,this.mPickResults.bHasGoHere]
         });
      }
      
      protected function HandleOptionsValueChanged(param1:Object) : void
      {
         this.mbSocialMenuDisabled = CommunicationManager.CallGameService("OptionsGetValue",{"name":"TradSocialMenuEnabled"});
      }
      
      protected function HandleSetModalVisible(param1:Boolean) : void
      {
         if(param1)
         {
            CommunicationManager.SendMessage("HidePieMenu",null);
         }
      }
      
      public function A11yAnnounceMenu(param1:int) : void
      {
         try
         {
            CommunicationManager.PostServerCommand("a11y.menuopen",param1.toString());
            TooltipManager.getInstance().A11yFocusInto(this);
         }
         catch(e:Error)
         {
         }
      }

      protected function HandlePieMenuCreate(param1:InteractionMenuData) : void
      {
         var _loc7_:FlyAwayText = null;
         var _loc8_:Point = null;
         var _a11yScanner:Boolean = TooltipManager["sA11yPick"] != null;
         try
         {
            TooltipManager["sA11yPick"] = null;
         }
         catch(e:Error)
         {
         }
         if(SystemUtils.UsingController && NavManager.Instance.CurrentFocusable is GameplayCenterDragAdapter)
         {
            CommunicationManager.SendUIMessage("LiveDragEnded");
         }
         if(param1.disabled_tooltip)
         {
            if(_a11yScanner)
            {
               this.A11yPostText("a11y.widget_enc",param1.disabled_tooltip.toString());
            }
            _loc7_ = new FlyAwayText();
            _loc7_.text = param1.disabled_tooltip.toString();
            _loc7_.type = FlyAwayText.FLYAWAY_TEXT_BAD;
            CommunicationManager.SendUIMessage("CreateFlyawayText",_loc7_);
            return;
         }
         var _loc2_:WorldPickResult = this.mPickResults;
         if(_loc2_ == null)
         {
            return;
         }
         var _loc3_:int = _loc2_.pickType;
         if(param1.items.length == 0 || _loc3_ == PieMenuConstants.PICK_MANAGE_OUTFIT || _loc3_ == PieMenuConstants.PICK_MANAGE_SMALL_BUSINESS_OUTFIT)
         {
            if(_a11yScanner)
            {
               this.A11yPostText("a11y.menuempty","1");
            }
            return;
         }
         if(param1.client_reference_id != this.mLastInteractionRequestId)
         {
            return;
         }
         this.A11yAnnounceMenu(param1.items.length);
         this.mMenuData = param1;
         var _loc4_:PieMenuBase = this.mcMenu;
         if(this.isInventoryRequest)
         {
            _loc8_ = globalToLocal(this.itemPosition);
            _loc4_.x = _loc8_.x;
            _loc4_.y = _loc8_.y;
            this.isInventoryRequest = false;
         }
         else
         {
            _loc4_.x = InputUtils.sMouseX - LayoutAPI.ScreenMargin.x;
            _loc4_.y = InputUtils.sMouseY - LayoutAPI.ScreenMargin.y;
         }
         var _loc5_:PieMenuButtonData = new PieMenuButtonData();
         var _loc6_:Boolean = !this.mbSocialMenuDisabled && !this.mbShiftOnPickup && !param1.supress_social_front_page;
         if(_loc2_)
         {
            this.mRoot = InteractionMenuData.GenerateTree(param1,PieMenuTunables.MAX_NUM_OPTIONS,_loc3_ == PieMenuConstants.PICK_SIM,_loc2_.objectId,_loc6_);
            _loc5_.simFirstName = _loc2_.simFirstName;
         }
         else
         {
            this.mRoot = InteractionMenuData.GenerateTree(param1,PieMenuTunables.MAX_NUM_OPTIONS,false,null,_loc6_);
            _loc5_.simFirstName = "";
         }
         _loc5_.data = this.mRoot;
         PieMenuButtonData.HasSocialFrontPage = _loc3_ == PieMenuConstants.PICK_SIM && _loc6_;
         _loc4_.Draw(_loc5_,{"isUpdate":true});
         CommunicationManager.SendMessage("ShowPieMenu",{
            "objectId":_loc2_.objectId,
            "lotId":_loc2_.lotId
         });
      }
      
      public function A11yOnOpenPieMenu(param1:Object) : void
      {
         var _loc2_:uint = 0;
         var _loc3_:WorldPickResult = null;
         try
         {
            this.mLastInteractionRequestId = this.mLastInteractionRequestId + 1;
            if(this.mLastInteractionRequestId == 0)
            {
               this.mLastInteractionRequestId = 1;
            }
            _loc2_ = this.mLastInteractionRequestId;
            this.isInventoryRequest = false;
            this.isCloseEvent = false;
            this.mbShiftOnPickup = false;
            _loc3_ = new WorldPickResult();
            _loc3_.pickType = int(param1.pickType);
            _loc3_.objectId = String(param1.objectId);
            _loc3_.worldPosX = Number(param1.x);
            _loc3_.worldPosY = Number(param1.y);
            _loc3_.worldPosZ = Number(param1.z);
            _loc3_.lotId = uint(param1.lotId);
            _loc3_.level = int(param1.level);
            _loc3_.simFirstName = String(param1.simFirstName);
            _loc3_.bHasGoHere = false;
            this.mPickResults = _loc3_;
            CommunicationManager.CallGameService("PostServerCommand",{
               "command":"interactions.choices",
               "commandArgs":[_loc3_.objectId,_loc3_.pickType,_loc3_.worldPosX,_loc3_.worldPosY,_loc3_.worldPosZ,_loc3_.lotId,_loc3_.level,0,0,0,_loc2_,0,0,true]
            });
         }
         catch(e:Error)
         {
         }
      }

      public function A11yPostText(param1:String, param2:String) : void
      {
         try
         {
            if(param2 != null && param2.length > 0)
            {
               CommunicationManager.PostServerCommand(param1,encodeURIComponent(param2));
            }
         }
         catch(e:Error)
         {
         }
      }

      protected function HandleForceDisableTravelBtn(param1:Object) : void
      {
         this.HandleToggleTravelButton(false);
         this.mbForceDisableTravelBtn = true;
      }
      
      protected function HandleToggleTravelButton(param1:Object) : void
      {
         var _loc2_:Boolean = false;
         var _loc3_:Array = null;
         var _loc4_:SimPB = null;
         var _loc5_:GameSaveLockUnlock = null;
         var _loc6_:Boolean = false;
         var _loc7_:LocKey = null;
         if(this.mbForceDisableTravelBtn)
         {
            return;
         }
         if(param1 as Boolean)
         {
            if(!this.mcMenu.visible)
            {
               if(!this.btnTravel.visible)
               {
                  this.btnTravel.visible = true;
                  InputActionManager.RegisterAction(this.mInputActionHideTravelBtn);
                  stage.addEventListener(FocusEvent.MOUSE_FOCUS_CHANGE,this.OnTravelBtnFocusChange,false,0,true);
                  stage.addEventListener(MouseEvent.CLICK,this.OnTravelBtnStageMouseClick,false,0,true);
                  stage.addEventListener(MouseEvent.MOUSE_DOWN,this.OnTravelBtnMouseDownOnStage,false,0,true);
               }
               this.SetTravelButtonPosition(this.btnTravel);
               _loc2_ = false;
               _loc3_ = GameplayStateData.SelectableSims;
               for each(_loc4_ in _loc3_)
               {
                  if(_loc4_.id == GameplayStateData.ActiveSimId)
                  {
                     _loc2_ = _loc4_.InZone;
                     break;
                  }
               }
               if(TutorialMode.IsFTUE())
               {
                  _loc2_ = false;
               }
               if(_loc2_)
               {
                  _loc5_ = GameplayStateData.SaveLockUnlockMessage;
                  _loc2_ = !_loc5_ || !_loc5_.is_locked;
                  this.btnTravel.enabled = _loc2_;
                  this.btnTravel.TooltipExt.SetText(!_loc2_ ? _loc5_.lock_reason : KeysGE.LOT_CONTEXT_MENU_TRAVEL);
               }
               else
               {
                  this.btnTravel.enabled = false;
                  this.btnTravel.TooltipExt.SetText(KeysGE.TRAVEL_INVALID_ACTIVE_SIM);
               }
               if(GameplayStateData.IsBlockingSituationRunning)
               {
                  this.btnTravel.enabled = false;
                  _loc6_ = GameplayStateData.IsCareerSituationRunning;
                  _loc7_ = _loc6_ ? KeysGP.TRAVEL_BTN_DISABLED_BY_CAREER : KeysGP.TRAVEL_BTN_DISABLED_BY_EVENT;
                  TooltipExtension.Get(this.btnTravel).SetText(_loc7_);
               }
            }
            if(this.btnTravel.visible)
            {
               if(Ticker.Has(this.btnTravel))
               {
                  Ticker.Reset(this.btnTravel);
               }
               else
               {
                  Ticker.Add(this.btnTravel,PieMenuTunables.TRAVEL_BUTTON_DISMISS_TIMER,this.OnTravelButtonDismissed);
               }
            }
         }
         else if(this.btnTravel.visible)
         {
            this.btnTravel.visible = false;
            Ticker.Remove(this.btnTravel);
            InputActionManager.UnregisterAction(this.mInputActionHideTravelBtn);
            stage.removeEventListener(FocusEvent.MOUSE_FOCUS_CHANGE,this.OnTravelBtnFocusChange);
            stage.removeEventListener(MouseEvent.CLICK,this.OnTravelBtnStageMouseClick);
            stage.removeEventListener(MouseEvent.MOUSE_DOWN,this.OnTravelBtnMouseDownOnStage);
         }
      }
      
      protected function SetTravelButtonPosition(param1:Button) : void
      {
         var _loc4_:Number = NaN;
         var _loc5_:Number = NaN;
         var _loc2_:Point = LayoutAPI.ScreenMargin;
         var _loc3_:Point = LayoutAPI.GetStageSize(false);
         param1.x = InputUtils.sMouseX - _loc2_.x;
         param1.y = InputUtils.sMouseY - _loc2_.y;
         _loc4_ = param1.width / 2;
         _loc5_ = param1.height / 2;
         var _loc6_:Point = new Point(param1.x - _loc4_,param1.y - _loc5_);
         var _loc7_:Point = new Point(param1.x + _loc4_,param1.y + _loc5_);
         if(_loc6_.x <= _loc2_.x + VirtualCursorConstants.CURSOR_MARGIN_LEFT)
         {
            param1.x += param1.width;
         }
         else if(_loc7_.x >= _loc3_.x - VirtualCursorConstants.CURSOR_MARGIN_RIGHT)
         {
            param1.x -= param1.width;
         }
         if(_loc6_.y <= _loc2_.y + VirtualCursorConstants.CURSOR_MARGIN_TOP)
         {
            param1.y += param1.height;
         }
         else if(_loc7_.y >= _loc3_.y - VirtualCursorConstants.CURSOR_MARGIN_BOTTOM)
         {
            param1.y -= param1.height;
         }
      }
      
      protected function HandleSituationStart(param1:Object) : void
      {
         if(this.btnTravel.visible)
         {
            this.btnTravel.enabled = false;
            (this.btnTravel.GetExtension(TooltipExtension) as TooltipExtension).SetText(KeysGP.TRAVEL_BTN_DISABLED_BY_EVENT);
         }
      }
      
      protected function HandleSituationEnd(param1:Object) : void
      {
         var _loc2_:GameSaveLockUnlock = null;
         if(this.btnTravel.visible)
         {
            _loc2_ = GameplayStateData.SaveLockUnlockMessage;
            this.btnTravel.enabled = !_loc2_.is_locked;
            (this.btnTravel.GetExtension(TooltipExtension) as TooltipExtension).SetText(_loc2_.is_locked ? _loc2_.lock_reason : null);
         }
      }
      
      protected function OnOptionSelected(param1:PieMenuEvent) : void
      {
         var _loc2_:InteractionMenuItem = param1.data as InteractionMenuItem;
         if(_loc2_.bDisabled)
         {
            return;
         }
         CommunicationManager.CallGameService("PostServerCommand",{
            "command":"interactions.select",
            "commandArgs":[_loc2_.id,this.mMenuData.server_reference_id]
         });
         CommunicationManager.SendMessage("HidePieMenu",{"isOptionSelected":true});
         if(this.mPickResults.mObjectInventoryId)
         {
            CommunicationManager.CallUIService("CloseObjectInventory",{});
         }
      }
      
      protected function OnMenuCancelled(param1:PieMenuEvent) : void
      {
         CommunicationManager.SendMessage("HidePieMenu",null);
      }
      
      protected function OnTravelButtonClicked(param1:PushButtonEvent) : void
      {
         if(!this.btnTravel.enabled || GameStateFlags.IsBetweenStates)
         {
            return;
         }
         if(param1.buttonIdx == MouseEventEx.LEFT_BUTTON)
         {
            CommunicationManager.SendMessage("SetAllowSimSwitch",false);
            GameStateFlags.IsBetweenStates = CommunicationManager.CallGameService("GoToNeighborhoodTravel");
            if(GameStateFlags.IsBetweenStates)
            {
               this.HandleToggleTravelButton(false);
            }
            else
            {
               CommunicationManager.SendMessage("SetAllowSimSwitch",true);
            }
         }
      }
      
      protected function OnTravelButtonDismissed(param1:TickerEvent) : void
      {
         this.HandleToggleTravelButton(false);
      }
      
      protected function OnOpenPieMenu(param1:Object) : void
      {
         var _loc2_:uint = ++this.mLastInteractionRequestId;
         if(_loc2_ == 0)
         {
            _loc2_ = ++this.mLastInteractionRequestId;
         }
         this.isInventoryRequest = true;
         var _loc3_:String = param1["objectId"] as String;
         _loc3_ = _loc3_ ? _loc3_ : "0";
         this.itemPosition = new Point(param1["posX"],param1["posY"]);
         this.itemPosition.x -= LayoutAPI.ScreenMargin.x;
         this.itemPosition.y -= LayoutAPI.ScreenMargin.y;
         var _loc4_:Object = param1["requestType"];
         var _loc5_:int = _loc4_ ? _loc4_ as int : PieMenuConstants.PICK_OBJECT;
         this.mPickResults = new WorldPickResult();
         this.mPickResults.pickType = _loc5_;
         this.mPickResults.objectId = _loc3_;
         var _loc6_:String = "0";
         if("inventoryObjectId" in param1 && Boolean(param1.inventoryObjectId))
         {
            _loc6_ = param1.inventoryObjectId;
            this.mPickResults.mObjectInventoryId = _loc6_;
         }
         var _loc7_:int = 0;
         var _loc8_:Array = [_loc3_,_loc5_,0,0,0,0,0,0,0,0,_loc2_,_loc6_,0,false];
         CommunicationManager.CallGameService("PostServerCommand",{
            "command":"interactions.choices",
            "commandArgs":_loc8_
         });
      }
      
      protected function DebugCommandCloseInteractionMenu(param1:Array, param2:Object, param3:String) : void
      {
         CommunicationManager.SendMessage("HidePieMenu",null);
      }
      
      protected function HandleEscapeKey() : Boolean
      {
         CommunicationManager.SendMessage("HidePieMenu",null);
         return false;
      }
      
      protected function HandleHideTravelBtn() : Boolean
      {
         this.HandleToggleTravelButton(false);
         return false;
      }
      
      protected function OnFocusChange(param1:FocusEvent) : void
      {
         if(!DisplayObjectUtils.IsParent(this,param1.relatedObject))
         {
            CommunicationManager.SendMessage("HidePieMenu",null);
         }
      }
      
      protected function OnStageMouseClick(param1:MouseEvent) : void
      {
         var _loc2_:MouseEventEx = param1 as MouseEventEx;
         if(Boolean(_loc2_) && _loc2_.buttonIdx == MouseEventEx.RIGHT_BUTTON)
         {
            CommunicationManager.SendMessage("HidePieMenu",null);
         }
      }
      
      protected function OnMouseDownOnStage(param1:MouseEvent) : void
      {
         var _loc2_:MouseEventEx = param1 as MouseEventEx;
         if(Boolean(_loc2_) && (_loc2_.buttonIdx == MouseEventEx.RIGHT_BUTTON || _loc2_.buttonIdx == MouseEventEx.MIDDLE_BUTTON))
         {
            CommunicationManager.SendMessage("HidePieMenu",null);
         }
      }
      
      protected function OnTravelBtnFocusChange(param1:FocusEvent) : void
      {
         if(!DisplayObjectUtils.IsParent(this,param1.relatedObject))
         {
            this.HandleToggleTravelButton(false);
         }
      }
      
      protected function OnTravelBtnStageMouseClick(param1:MouseEvent) : void
      {
         var _loc2_:MouseEventEx = param1 as MouseEventEx;
         if(Boolean(_loc2_) && _loc2_.buttonIdx == MouseEventEx.RIGHT_BUTTON)
         {
            this.HandleToggleTravelButton(false);
         }
      }
      
      protected function OnTravelBtnMouseDownOnStage(param1:MouseEvent) : void
      {
         var _loc2_:MouseEventEx = param1 as MouseEventEx;
         if(Boolean(_loc2_) && (_loc2_.buttonIdx == MouseEventEx.RIGHT_BUTTON || _loc2_.buttonIdx == MouseEventEx.MIDDLE_BUTTON))
         {
            this.HandleToggleTravelButton(false);
         }
      }
      
      protected function InitGamepad() : void
      {
         this.mInputAdapter = new DynamicOmnidirectionalAdapter(null);
         this.mInputAdapter.OnBackCall(this.GoBack);
         AddMessageListener("GamepadFocusPieMenu",this.HandleGamepadFocusPieMenu);
         if(SystemUtils.UsingMouseKeyboard)
         {
            AddMessageListener("UsingControllerToggled",this.HandleUsingControllerToggled);
         }
      }
      
      protected function GoBack() : void
      {
         this.mcMenu.GoBack();
      }
      
      override public function Enter(param1:EnterParams = null) : IInputFocusable
      {
         AddMessageListener("CursorModeToggled",this.HandleCursorModeToggled);
         return this.mInputAdapter.Enter(param1);
      }
      
      override public function Exit() : void
      {
         super.Exit();
         this.mInputAdapter.Exit();
      }
      
      override public function OnExited() : void
      {
         super.OnExited();
         RemoveMessageListener("CursorModeToggled",this.HandleCursorModeToggled);
      }
      
      override public function OnEntered(param1:EnterParams = null) : void
      {
         if(CommunicationManager.CallUIService("IsModalVisible"))
         {
            CommunicationManager.SendMessage("HidePieMenu",null);
            return;
         }
         super.OnEntered(param1);
         if(param1.mDirection == NavDirection.BACK && !this.mcMenu.visible)
         {
            NavManager.Instance.TryFocusBack(this.mInputAdapter);
         }
      }
      
      protected function HandleCursorModeToggled() : void
      {
         CommunicationManager.SendMessage("HidePieMenu",null);
         this.HandleToggleTravelButton(false);
      }
      
      protected function HandleGamepadFocusPieMenu() : void
      {
         if(!this.mInputAdapter.GetContainer())
         {
            this.mInputAdapter.SetContainer(this.mcMenu);
         }
         this.mInputAdapter.ResetHighlight();
      }
      
      protected function HandleUsingControllerToggled() : void
      {
         var _loc1_:Button = null;
         if(SystemUtils.UsingController)
         {
            if(!this.mInputAdapter.GetContainer())
            {
               this.mInputAdapter.SetContainer(this.mcMenu);
            }
            _loc1_ = this.mcMenu.GetCurrentMouseOverButton();
            if(_loc1_)
            {
               this.mInputAdapter.SetHighlightedObject(_loc1_);
            }
            else
            {
               this.mInputAdapter.ResetHighlight();
            }
         }
      }
   }
}

