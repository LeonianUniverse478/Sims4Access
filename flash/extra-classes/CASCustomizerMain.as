package widgets.CAS.Customizer
{
   import flash.display.DisplayObject;
   import flash.display.DisplayObjectContainer;
   import flash.display.MovieClip;
   import flash.display.Sprite;
   import flash.events.Event;
   import flash.events.MouseEvent;
   import flash.geom.Point;
   import flash.ui.Keyboard;
   import flash.text.TextField;
   import flash.utils.getQualifiedClassName;
   import flash.utils.getTimer;
   import gamedata.CAS.CASAPI;
   import gamedata.CAS.ContextMenu.CASContextMenuItem;
   import gamedata.CAS.shared.CASConfiguration;
   import gamedata.CAS.shared.CASStateData;
   import gamedata.CAS.shared.SimInfo;
   import gamedata.shared.OccultTypes;
   import gamedata.shared.SimAgeTypes;
   import gamedata.shared.Species;
   import olympus.constants.ActionCodes;
   import olympus.constants.GameStates;
   import olympus.constants.InputActionPriorities;
   import olympus.constants.Layers;
   import olympus.controls.GUIComponent;
   import olympus.core.widget.WidgetBase;
   import olympus.events.GenericEvent;
   import olympus.events.TweenEvent;
   import olympus.extensions.CASTelemetryExtension;
   import olympus.extensions.TutorialTipExtension;
   import olympus.gamepad.EnterParams;
   import olympus.gamepad.LayoutAPI;
   import olympus.gamepad.NavDirection;
   import olympus.gamepad.NavManager;
   import olympus.gui.lists.ScrollList;
   import olympus.input.IInputFocusable;
   import olympus.input.InputAction;
   import olympus.input.InputTrigger;
   import olympus.input.adapters.BidirectionalGroupAdapter;
   import olympus.input.adapters.GridInputAdapter;
   import olympus.input.adapters.InputAdapterConfirmEvent;
   import olympus.input.adapters.InputAdapterEvent;
   import olympus.input.adapters.InputAdapterLeaveEvent;
   import olympus.input.helpers.ScrollListHelper;
   import olympus.io.CommunicationManager;
   import olympus.io.InputActionManager;
   import olympus.layout.GridLayout;
   import olympus.localization.KeysConsole;
   import olympus.localization.LocKey;
   import olympus.motion.Animation;
   import olympus.motion.Tween;
   import olympus.utils.SystemUtils;
   import widgets.CAS.Customizer.Panes.Breeds.BreedsMixerPane;
   import widgets.CAS.FilterPane.CASFilterPaneTunables;
   import widgets.CAS.constants.CASBodyType;
   import widgets.CAS.constants.CASContextMenuState;
   import widgets.CAS.constants.CASMode;
   import widgets.CAS.constants.CASSubStates;
   import widgets.CAS.constants.CASTunables;
   import widgets.CAS.constants.CursorIconType;
   import widgets.CAS.constants.MenuState;
   import widgets.CAS.constants.ShiftCameraTunables;
   import widgets.CAS.controls.CASBodyTypePanel;
   import widgets.CAS.controls.CASBreedCatalogCellView;
   import widgets.CAS.controls.CASClothingPanelCellViewMain;
   import widgets.CAS.controls.CASFilterPane;
   import widgets.CAS.controls.CASGenericCatalogVariantCellView;
   import widgets.CAS.controls.CASLayerComponent;
   import widgets.CAS.controls.ColorSwatchPanel;
   import widgets.CAS.controls.ColorSwatchPanelCellView;
   import widgets.CAS.controls.HairGrowthPanel;
   import widgets.CAS.events.CASCatalogEvent;
   import widgets.CAS.gamepad.CASActionCodes;
   import widgets.CAS.gamepad.CASSharedActions;
   import widgets.CAS.gamepad.adapters.CASCenterMainAdapter;
   import widgets.shared.constants.TutorialTipUIElement;
   
   [Embed(source="/_assets/assets.swf", symbol="symbol500")]
   public class CASCustomizerMain extends WidgetBase
   {
      
      protected static var sHasPendingEdits:Boolean = false;
      
      public var mcBodyModPanel:BodyModPanel;
      
      public var mcFaceModPanel:FaceModPanel;
      
      public var mcClothingPanel:ClothingPanel;
      
      public var mcDetailedEditModePanel:DetailedEditModePanel;
      
      public var mcBodyModSliderPanel:BodyModSliderPanel;
      
      public var mcFeaturedFaceLookPanel:FeaturedFaceLookPanel;
      
      public var mcGenericCatalogPanel:GenericCatalogPanel;
      
      public var mcSkinColorPanel:SkinTonePanel;
      
      public var mcGhostToggle:GhostPreviewToggle;
      
      public var mcWingToggle:WingModeToggle;
      
      public var mcCursorAttachment:MovieClip;
      
      protected var mIsMouseDragging:Boolean = false;
      
      protected var mCurrCursorType:uint = 0;
      
      protected var mbFromInputAction:Boolean = false;
      
      protected var mCurrState:int = MenuState.NONE;
      
      protected var mNextState:int = MenuState.NONE;
      
      protected var mCurrSimInfo:SimInfo;
      
      protected var mEscInputAction:InputAction;
      
      protected var mLayerPanels:Sprite = new Sprite();
      
      protected var mbFullEditingEnabled:Boolean;
      
      protected var mbMouseLocked:Boolean = false;
      
      protected var mCASTelemetry:CASTelemetryExtension;
      
      protected var mCurrFilterTagType:int = 0;
      
      protected var mContextMenuState:int;
      
      protected var mForceFilterPaneRefresh:Boolean = false;
      
      protected var mbGameDrivenStateChange:Boolean = false;
      
      protected var mPanels:Array;
      
      protected var mCurrentPanel:CatalogPanel;
      
      protected var mInputAdapter:GridInputAdapter;
      
      protected var mFilterBubbleAdapter:BidirectionalGroupAdapter;
      
      protected var mResetInputAdapterHighlight:Boolean;
      
      protected var mbGamepadWaitingForCurrentPanel:Boolean = false;
      
      protected var mGamepadRandomizeAction:InputAction;
      
      protected var mbGamepadRandomizeEnabled:Boolean = false;
      
      protected var mGamepadTopSectionAction:InputAction;
      
      public function CASCustomizerMain()
      {
         super();
         this.mEscInputAction = InputAction.WhenTriggered(InputTrigger.FromKeyBinding(Keyboard.ESCAPE)).CallFunction(this.BeforeShowingExitMenu).RestrictToGameStates(GameStates.CAS).SetPriority(InputActionPriorities.ESC_CURSOR).SetLowPriority(InputActionPriorities.LOW_PRIORITY);
      }
      
      override public function Initialize() : void
      {
         var _loc2_:CatalogPanel = null;
         super.Initialize();
         var _loc1_:Sprite = this.mLayerPanels;
         addChild(_loc1_);
         _loc2_ = this.mcBodyModPanel;
         _loc2_.width = CASCustomizerTunables.CATALOG_WIDTH;
         _loc2_.x = 0;
         _loc2_.y = CASCustomizerTunables.BODYPANEL_TOP_MARGIN;
         _loc2_.visible = false;
         _loc1_.addChild(_loc2_);
         _loc2_ = this.mcSkinColorPanel;
         _loc2_.width = CASCustomizerTunables.CATALOG_WIDTH;
         _loc2_.x = 0;
         _loc2_.y = CASCustomizerTunables.BODYPANEL_TOP_MARGIN;
         _loc2_.visible = false;
         _loc1_.addChild(_loc2_);
         _loc2_ = this.mcFaceModPanel;
         _loc2_.width = CASCustomizerTunables.CATALOG_WIDTH;
         _loc2_.x = 0;
         _loc2_.y = CASCustomizerTunables.FACE_PANEL_TOP_MARGIN;
         _loc2_.visible = false;
         _loc1_.addChild(_loc2_);
         _loc2_ = this.mcClothingPanel;
         _loc2_.width = CASCustomizerTunables.CATALOG_WIDTH;
         _loc2_.x = 0;
         _loc2_.y = CASCustomizerTunables.PANEL_TOP_MARGIN;
         _loc2_.visible = false;
         _loc1_.addChild(_loc2_);
         _loc2_ = this.mcFeaturedFaceLookPanel;
         _loc2_.width = CASCustomizerTunables.CATALOG_WIDTH;
         _loc2_.x = 0;
         _loc2_.y = CASCustomizerTunables.FACE_PANEL_TOP_MARGIN;
         _loc2_.visible = false;
         _loc1_.addChild(_loc2_);
         _loc2_ = this.mcGenericCatalogPanel;
         _loc2_.width = CASCustomizerTunables.CATALOG_WIDTH;
         _loc2_.x = 0;
         _loc2_.y = CASCustomizerTunables.GENERICPANEL_TOP_MARGIN;
         _loc2_.visible = false;
         _loc1_.addChild(_loc2_);
         this.mPanels = [this.mcBodyModPanel,this.mcFaceModPanel,this.mcClothingPanel,this.mcFeaturedFaceLookPanel,this.mcGenericCatalogPanel,this.mcSkinColorPanel];
         this.mcDetailedEditModePanel.visible = false;
         this.mcBodyModSliderPanel.visible = false;
         this.mcGhostToggle.visible = false;
         this.mcWingToggle.visible = false;
         this.mcCursorAttachment.mcMainCursor.visible = false;
         this.HideDMBoundaryIndicators();
         var _loc3_:DisplayObjectContainer = CommunicationManager.CallUIService("GetLayer",{"layer":Layers.ALWAYS_ON_TOP_NO_INPUT}) as DisplayObjectContainer;
         _loc3_.addChild(this.mcCursorAttachment);
         CommunicationManager.CallGameService("BindDisplayObject",{
            "displayObject":this.mcCursorAttachment,
            "attachPoint":"MOUSE"
         });
         AddMessageListener("CASContextMenuSetMenuState",this.HandleContextMenuSetMenuState);
         AddMessageListener("CASShowCursorAttachment",this.HandleShowCursorAttachment);
         AddMessageListener("MouseIsOnUI",this.HandleMouseEnterLeaveUI);
         AddMessageListener("CASSetSimInfo",this.HandleSetSimInfo,SimInfo);
         AddMessageListener("CASChangeMenuState",this.HandleMenuStateChange);
         AddMessageListener("CASHideCustomizer",this.HandleHideRequest);
         AddMessageListener("CASContextMenuStateChanged",this.HandleContextMenuUpdate);
         AddMessageListener("CasBackOutUI",this.HandleBackOutUI);
         AddMessageListener("CasUndoEnabled",this.HandleUndoEnabled);
         AddMessageListener("ToggleFeaturedLooksMode",this.HandleToggleFeaturedLooksMode);
         AddMessageListener("CasRemoveSelectedParts",this.HandleRemoveSelectedParts);
         AddMessageListener("CasNotifyZoomModeChange",this.HandleZoomModeChanged);
         AddMessageListener("CASBindingSimContextMenu",this.HandleAlignToContextMenu);
         AddMessageListener("CASRefreshMTXUI",this.HandleNewMtxContentAvailable);
         AddMessageListener("CASHideCursorAttachment",this.HandleHideCursorAttachment);
         AddMessageListener("CASPostPerformUndo",this.HandlePostUndoRedo);
         AddMessageListener("CASPostPerformRedo",this.HandlePostUndoRedo);
         if(SystemUtils.UsingController)
         {
            AddMessageListener("TabThroughOutfits",this.HandleGamepadTabThroughOutfits);
            AddMessageListener("CASCustomizerFocusOnHighlightedPanel",this.GamepadOpenVariations);
            AddMessageListener("CASCustomizerHighlightSelected",this.HighlightSelectedItem);
         }
         AddMessageListener("CASPhysiqueValues",this.HandleCASPhysiqueValues);
         AddMessageListener("RefreshSimAgeGender",this.RefreshSimAge);
         RegisterServiceHandler("CASAbortFaceDetailMode",this.AbortFaceDetailMode);
         this.AlignComponents();
         var _loc4_:SimInfo = new SimInfo(CommunicationManager.CallGameService("CASGetSimInfo",null,true));
         this.mCurrSimInfo = _loc4_;
         InputActionManager.RegisterAction(this.mEscInputAction);
         ShiftCameraTunables.RegisterUI(ShiftCameraTunables.BODYMOD_CATALOG);
         ShiftCameraTunables.RegisterUI(ShiftCameraTunables.CLOTHING_CATALOG);
         ShiftCameraTunables.RegisterUI(ShiftCameraTunables.FACEMOD_CATALOG);
         ShiftCameraTunables.RegisterUI(ShiftCameraTunables.FEATURED_FACE_LOOKS_CATALOG);
         ShiftCameraTunables.RegisterUI(ShiftCameraTunables.GENERIC_CATALOG);
         this.mCASTelemetry = GetExtension(CASTelemetryExtension) as CASTelemetryExtension;
         this.HandleSetSimInfo(_loc4_);
         if(SystemUtils.UsingConsoleInputMode)
         {
            this.InitGamepad();
         }
         this.A11yHookCasStage();
      }

      // a11y: CAS renders on its OWN stage, and the live TooltipManager's
      // mouse listener is bound to the live-mode stage, so CAS was totally
      // silent (2026-08-03: not even a mouse-over heartbeat). Patching
      // TooltipManager into CASLibrary did NOT help either, because
      // ClassLibraryGamedata already won that class name for the whole
      // application domain, so the CAS copy is never loaded.
      //
      // The hook lives here because CASCustomizerMain is defined in exactly
      // ONE movie (checked against all 258), so nothing can shadow it,
      // the same property that made the MoodContainer fix work.
      //
      // *** DO NOT REFERENCE olympus.core.TooltipManager FROM THIS FILE. ***
      // CASCustomizer does not contain that class. A first attempt forwarded
      // events to TooltipManager.getInstance() and HARD-CRASHED the client
      // on entering CAS (2026-08-03): the AVM must resolve the class when it
      // verifies the method, which happens BEFORE any try/catch inside it
      // can run, so the failure is a native crash with no script error and
      // no log line. FFDec was exonerated by a tag-level diff: every tag
      // but the bytecode block was byte-identical. So this collector is
      // deliberately self-contained: it only uses classes CASCustomizer
      // already owns, and posts the same y|x|text payload the Python side
      // already knows how to order and clean up.
      protected var mA11yCasHooked:Boolean = false;

      protected var mA11yCasLast:DisplayObject = null;

      protected var mA11yCasLastText:String = "";

      protected static var sA11yCasDiag:int = 0;

      public function A11yHookCasStage() : void
      {
         try
         {
            if(this.mA11yCasHooked)
            {
               return;
            }
            if(stage == null)
            {
               // Not on the stage yet; retry when we are.
               addEventListener(Event.ADDED_TO_STAGE,this.A11yOnCasStaged,false,0,true);
               return;
            }
            this.mA11yCasHooked = true;
            stage.addEventListener(MouseEvent.MOUSE_OVER,this.A11yOnCasOver,true,0,true);
            CommunicationManager.PostServerCommand("a11y.mark","cashook-CASCustomizer");
         }
         catch(e:Error)
         {
         }
      }

      public function A11yOnCasStaged(param1:Event) : void
      {
         try
         {
            removeEventListener(Event.ADDED_TO_STAGE,this.A11yOnCasStaged);
         }
         catch(e:Error)
         {
         }
         this.A11yHookCasStage();
      }

      public function A11yCasWidget(param1:DisplayObject) : DisplayObject
      {
         var _loc2_:DisplayObject = param1;
         var _loc3_:int = 0;
         var _loc4_:Sprite = null;
         var _loc5_:String = null;
         while(_loc2_ != null && _loc3_ < 8)
         {
            _loc5_ = getQualifiedClassName(_loc2_);
            if(_loc5_.indexOf("CellView") >= 0 || _loc5_.indexOf("Button") >= 0 || _loc5_.indexOf("Checkbox") >= 0)
            {
               return _loc2_;
            }
            _loc4_ = _loc2_ as Sprite;
            if(_loc4_ != null && _loc4_.buttonMode)
            {
               return _loc2_;
            }
            _loc2_ = _loc2_.parent;
            _loc3_++;
         }
         return param1 is TextField ? param1.parent : null;
      }

      public function A11yCasCollect(param1:DisplayObject, param2:Array, param3:int) : void
      {
         var _loc4_:TextField = null;
         var _loc5_:DisplayObjectContainer = null;
         var _loc6_:int = 0;
         var _loc7_:Point = null;
         if(param1 == null || param2.length > 12 || param3 > 8)
         {
            return;
         }
         _loc4_ = param1 as TextField;
         if(_loc4_ != null)
         {
            if(_loc4_.visible && _loc4_.text != null && _loc4_.text.length > 0)
            {
               _loc7_ = _loc4_.localToGlobal(new Point(0,0));
               param2.push(int(_loc7_.y).toString() + "|" + int(_loc7_.x).toString() + "|" + _loc4_.text);
            }
            return;
         }
         _loc5_ = param1 as DisplayObjectContainer;
         if(_loc5_ != null)
         {
            if(param3 > 0 && !_loc5_.visible)
            {
               return;
            }
            _loc6_ = 0;
            while(_loc6_ < _loc5_.numChildren)
            {
               this.A11yCasCollect(_loc5_.getChildAt(_loc6_),param2,param3 + 1);
               _loc6_++;
            }
         }
      }

      public function A11yOnCasOver(param1:MouseEvent) : void
      {
         var _loc2_:DisplayObject = null;
         var _loc3_:Array = null;
         var _loc4_:String = null;
         var _loc5_:String = null;
         try
         {
            if(getTimer() - sA11yCasDiag > 20000)
            {
               sA11yCasDiag = getTimer();
               CommunicationManager.PostServerCommand("a11y.mark","casover-CASCustomizer");
            }
            _loc2_ = param1.target as DisplayObject;
            if(_loc2_ == null)
            {
               return;
            }
            _loc2_ = this.A11yCasWidget(_loc2_);
            if(_loc2_ == null || _loc2_ == this.mA11yCasLast)
            {
               return;
            }
            this.mA11yCasLast = _loc2_;
            _loc3_ = new Array();
            this.A11yCasCollect(_loc2_,_loc3_,0);
            if(_loc3_.length == 0)
            {
               return;
            }
            _loc4_ = _loc3_.join("");
            if(_loc4_ == this.mA11yCasLastText)
            {
               return;
            }
            this.mA11yCasLastText = _loc4_;
            if(_loc4_.length > 1400)
            {
               _loc4_ = _loc4_.substr(0,1400);
            }
            _loc5_ = encodeURIComponent(_loc4_);
            _loc5_ = _loc5_.split("'").join("%27");
            _loc5_ = _loc5_.split("(").join("%28");
            _loc5_ = _loc5_.split(")").join("%29");
            _loc5_ = _loc5_.split("!").join("%21");
            _loc5_ = _loc5_.split("~").join("%7E");
            _loc5_ = _loc5_.split("*").join("%2A");
            CommunicationManager.PostServerCommand("a11y.widget_enc",_loc5_);
         }
         catch(e:Error)
         {
         }
      }
      
      override public function Show(param1:Object = null) : void
      {
         super.Show(param1);
         if(CASConfiguration.IsTattooOnlyMode)
         {
            this.HandleContextMenuSetMenuState({"menuState":MenuState.CLOTHING_BODY_TATTOOS});
            this.ShowClothingPanel(this.mCurrState);
         }
      }
      
      override public function Unload() : void
      {
         super.Unload();
         addChild(this.mcCursorAttachment);
         CommunicationManager.CallGameService("UnbindDisplayObject",{"displayObject":this.mcDetailedEditModePanel});
         CommunicationManager.CallGameService("UnbindDisplayObject",{"displayObject":this.mcBodyModSliderPanel});
         CommunicationManager.CallGameService("UnbindDisplayObject",{"displayObject":this.mcCursorAttachment});
         CommunicationManager.CallGameService("UnbindDisplayObject",{"displayObject":this.mLayerPanels});
         CommunicationManager.CallGameService("UnbindDisplayObject",{"displayObject":this.mcGhostToggle});
         CommunicationManager.CallGameService("UnbindDisplayObject",{"displayObject":this.mcWingToggle});
         InputActionManager.UnregisterAction(this.mEscInputAction);
      }
      
      override public function HandleStageResized(param1:Number, param2:Number) : void
      {
         super.HandleStageResized(param1,param2);
         this.AlignComponents();
         this.mcBodyModSliderPanel.y = param2 * CASCustomizerTunables.BODYPANEL_SLIDERBOX_STAGE_POSITION_Y_PERCENT;
         this.mcDetailedEditModePanel.y = (param2 - this.mcDetailedEditModePanel.height) * CASCustomizerTunables.DETAILED_EDIT_MODE_PANEL_STAGE_POSITION_Y_PERCENT;
         this.PositionGhostToggle();
         this.PositionWingToggle();
         ShiftCameraTunables.NotifyStageResize();
      }
      
      protected function HandleAlignToContextMenu(param1:Object) : void
      {
         var _loc2_:Number = param1["view_x_offset"] as Number;
         var _loc3_:Number = (param1["screen_x_offset"] as Number) + CASCustomizerTunables.PANEL_SCREEN_OFFSET_X;
         var _loc4_:Number = param1["screen_x_max"] as Number;
         if(SystemUtils.UsingConsoleInputMode)
         {
            _loc4_ += CASTunables.SIM_ATTACH_PANEL_LEGEND_OFFSET;
         }
         this.BindDisplayObjectToSim(this.mLayerPanels,_loc2_,_loc3_,_loc4_);
         var _loc5_:Object = CASTunables.GetSimAttachOpts(this.mCurrSimInfo.speciesType,this.mCurrSimInfo.age);
         this.BindDisplayObjectToSim(this.mcBodyModSliderPanel,_loc5_.bodymod_panel.viewOffset.x,_loc5_.bodymod_panel.screenOffset.x,0);
         this.BindDisplayObjectToSim(this.mcDetailedEditModePanel,_loc5_.detailmode_panel.viewOffset.x,_loc5_.detailmode_panel.screenOffset.x,0);
         this.BindDisplayObjectToSim(this.mcGhostToggle,_loc5_.ghost_toggle.viewOffset.x,_loc5_.ghost_toggle.screenOffset.x,0,CASCustomizerTunables.GHOST_TOGGLE_MIN_X);
         this.BindDisplayObjectToSim(this.mcWingToggle,_loc5_.wing_toggle.viewOffset.x,_loc5_.wing_toggle.screenOffset.x,0);
      }
      
      protected function HandleNewMtxContentAvailable(param1:Object) : void
      {
         if(this.mcClothingPanel.IsVisible())
         {
            this.mcClothingPanel.RefreshMtx(this.mCurrState);
         }
      }
      
      protected function HandleRemoveSelectedParts(param1:Object) : void
      {
         var _loc3_:Object = null;
         var _loc4_:Array = null;
         var _loc5_:Array = null;
         var _loc6_:Array = null;
         var _loc7_:CatalogPanel = null;
         var _loc8_:Object = null;
         var _loc2_:Array = param1["selections"] as Array;
         if(_loc2_)
         {
            for each(_loc3_ in _loc2_)
            {
               _loc4_ = new Array();
               _loc5_ = new Array();
               if(_loc3_.tag != 0)
               {
                  _loc4_.push(_loc3_.tag);
               }
               if(_loc3_.tag_exclude != 0)
               {
                  _loc5_.push(_loc3_.tag_exclude);
               }
               CASAPI.ClearCatalogSlotSelected(_loc3_.menuState,_loc4_,_loc5_);
               _loc6_ = this.mPanels;
               for each(_loc7_ in _loc6_)
               {
                  if(_loc7_.IsVisible())
                  {
                     _loc7_.NotifyRemovedParts(new Array(),_loc3_.menuState);
                     break;
                  }
               }
               if(_loc3_.menuState == MenuState.CLOTHING_BODY_WINGS && this.mCurrState != MenuState.CLOTHING_BODY_WINGS)
               {
                  _loc8_ = {
                     "component_name":"PAINT_MODE",
                     "toggle":false
                  };
                  CommunicationManager.SendUIMessage("CASToggleContextMenuItem",_loc8_);
                  CommunicationManager.SendUIMessage("CASHideWingToggleAndShowWings");
               }
            }
         }
      }
      
      protected function HandleZoomModeChanged(param1:Object) : void
      {
         var _loc2_:int = param1 as int;
         this.mLayerPanels.visible = _loc2_ != CASMode.FACE_DETAIL;
      }
      
      protected function HandleCASPhysiqueValues(param1:Object) : void
      {
         this.mcBodyModSliderPanel.HandleCASPhysiqueValues(param1);
      }
      
      protected function RefreshSimAge(param1:Object) : void
      {
         this.mcBodyModSliderPanel.RefreshSimAge(param1);
      }
      
      protected function AbortFaceDetailMode(param1:Object) : void
      {
         if(this.mcDetailedEditModePanel.IsActive())
         {
            this.mcDetailedEditModePanel.ToggleAdvancedMode();
            ShiftCameraTunables.ClearCachedUIVisibilityMap();
            if(SystemUtils.UsingController)
            {
               CommunicationManager.CallGameService("CasSetCameraModeBody");
            }
         }
      }
      
      protected function BindDisplayObjectToSim(param1:DisplayObject, param2:Number, param3:Number, param4:Number, param5:Number = 0) : void
      {
         var _loc6_:String = CommunicationManager.CallGameService("CasGetSimSceneObjectId") as String;
         if(_loc6_)
         {
            CommunicationManager.CallGameService("BindDisplayObject",{
               "displayObject":param1,
               "objectId":_loc6_,
               "attachPoint":CASCustomizerTunables.PANEL_ATTACH_BONE,
               "viewOffset":{"x":param2},
               "screenOffset":{"x":param3},
               "lockY":true,
               "lockVisibility":true,
               "clampX":{
                  "min":param5,
                  "max":LayoutAPI.StageWidth - param4
               }
            });
         }
      }
      
      protected function AlignComponents() : void
      {
         var _loc3_:Number = NaN;
         var _loc4_:Array = null;
         var _loc5_:CatalogPanel = null;
         var _loc1_:int = int(LayoutAPI.StageHeight);
         if(CASConfiguration.IsFashionMode)
         {
            _loc3_ = _loc1_ - (CASCustomizerTunables.FASHION_SHOPPING_CART_HEIGHT + CASCustomizerTunables.GAP_BETWEEN_CATALOG_AND_GAMETRAY_BOTTOM_BAR);
         }
         else
         {
            _loc3_ = _loc1_ - (CASCustomizerTunables.GAMETRAY_BOTTOM_BAR_HEIGHT + CASCustomizerTunables.GAP_BETWEEN_CATALOG_AND_GAMETRAY_BOTTOM_BAR);
         }
         var _loc2_:Point = this.globalToLocal(new Point(0,_loc3_).add(LayoutAPI.ScreenMargin));
         if(this.mPanels)
         {
            _loc4_ = this.mPanels;
            for each(_loc5_ in _loc4_)
            {
               _loc5_.backgroundHeight = _loc2_.y - _loc5_.y;
            }
         }
      }
      
      protected function SetState(param1:int, param2:Boolean = true, param3:Boolean = false, param4:Boolean = true) : void
      {
         var _loc8_:Boolean = false;
         var _loc5_:int = this.mCurrFilterTagType;
         var _loc6_:CASContextMenuItem = CommunicationManager.CallUIService("CasGetCurrentContextData") as CASContextMenuItem;
         if(_loc6_)
         {
            this.mCurrFilterTagType = _loc6_.tag;
         }
         this.mNextState = param1;
         var _loc7_:int = this.mCurrState;
         if(_loc7_ != this.mNextState)
         {
            if(param2)
            {
               CommunicationManager.CallGameService("SetCasMenuState",param1);
            }
            _loc8_ = this.mCurrentPanel != null;
            this.OnLeaveState(_loc7_,param3);
            this.OnEnterState(param1,param3,param4);
            this.mCurrState = param1;
            if(!this.mCurrentPanel && _loc8_)
            {
               CommunicationManager.SendUIMessage("CASCustomizerPanelHidden");
               TutorialTipExtension.Get(this.mcClothingPanel).MarkVisibility(false);
            }
            this.mResetInputAdapterHighlight = true;
         }
         else if(_loc5_ != this.mCurrFilterTagType)
         {
            if(MenuState.SupportsTagDrivenSubMenu(this.mCurrState) || MenuState.SupportsTagDrivenMenu(this.mCurrState))
            {
               this.ShowClothingPanel(_loc7_);
            }
            this.mResetInputAdapterHighlight = true;
         }
         if(Species.IsPet(this.mCurrSimInfo.speciesType))
         {
            this.mcGhostToggle.isBreedPanelVisible = param1 == MenuState.PROFILE_GENERIC_FULL_BREED;
            if(param1 == MenuState.PROFILE_HEAD_MOUTH || param1 == MenuState.PROFILE_HEAD_JAW)
            {
               return;
            }
         }
         if(Boolean(SystemUtils.UsingController) && param1 != MenuState.NONE && param1 != MenuState.CLOTHING_LOOKS)
         {
            NavManager.Instance.FocusWidgetForward(WidgetName);
         }
      }
      
      protected function OnLeaveState(param1:int, param2:Boolean) : void
      {
         var _loc3_:int = MenuState.GetMenuMode(param1);
         var _loc4_:int = this.mNextState;
         switch(_loc3_)
         {
            case MenuState.MenuMode_PROFILE:
               if(this.mCurrentPanel)
               {
                  if(param2)
                  {
                     this.mCurrentPanel.SkipAnimation();
                  }
                  this.HidePanel(this.mCurrentPanel);
               }
               break;
            case MenuState.MenuMode_CLOTHING:
            case MenuState.MenuMode_ACCESSORIES:
               switch(param1)
               {
                  case MenuState.CLOTHING_BODYSCAR:
                  case MenuState.CLOTHING_BODYDETAILS:
                  case MenuState.CLOTHING_BODY_TATTOOS:
                  case MenuState.CLOTHING_BODY_MEDICAL:
                  case MenuState.CLOTHING_BODY_BODYHAIR_ARM:
                  case MenuState.CLOTHING_BODY_BODYHAIR_LEG:
                  case MenuState.CLOTHING_BODY_BODYHAIR_TORSOFRONT:
                  case MenuState.CLOTHING_BODY_BODYHAIR_TORSOBACK:
                     if(CASStateData.sCASSubState != CASSubStates.PETPAINTING)
                     {
                        CASStateData.TattooMode = false;
                        this.HandleSwitchTutorialTipControlEnum(TutorialTipUIElement.CAS_CLOTHING_PANEL);
                     }
                     break;
                  case MenuState.CLOTHING_FACE_TEETH:
                     CommunicationManager.CallGameService("ShowTeeth",false);
               }
               if(param2)
               {
                  this.mcClothingPanel.SkipAnimation();
               }
               this.HideClothingPanel();
               if(MenuState.ShouldZoomHands(param1) && !MenuState.ShouldZoomHands(_loc4_) || MenuState.IsTattoo(param1) && !MenuState.IsTattoo(_loc4_) && !CASConfiguration.IsTattooOnlyMode)
               {
                  CommunicationManager.CallGameService("CasSetZoomState",{
                     "zoomState":CASMode.BODY,
                     "playAudio":true
                  });
               }
               break;
            case MenuState.MenuMode_FEATURED:
               if(param1 == MenuState.FEATURED_FACE_PRESETS)
               {
                  CommunicationManager.CallGameService("ShowTeeth",false);
                  if(param2)
                  {
                     this.mcFeaturedFaceLookPanel.SkipAnimation();
                  }
                  this.HideFeaturedFaceLookPanel();
               }
         }
         if(param1 == MenuState.CLOTHING_LOOKS)
         {
            this.HideLooksPanel();
         }
      }
      
      protected function OnEnterState(param1:int, param2:Boolean, param3:Boolean = true) : void
      {
         var _loc8_:CASBodyTypePanel = null;
         var _loc4_:int = MenuState.GetMenuType(param1);
         var _loc5_:int = MenuState.GetMenuMode(param1);
         var _loc6_:int = MenuState.GetMenuSection(param1);
         var _loc7_:int = MenuState.GetGenericPanelType(param1,this.mCurrSimInfo);
         if(_loc7_ != MenuState.GENERICPANELTYPE_UNKNOWN)
         {
            this.ShowGenericCatalogPanel(param1,_loc7_);
            return;
         }
         switch(_loc5_)
         {
            case MenuState.MenuMode_PROFILE:
               switch(_loc6_)
               {
                  case MenuState.MenuSection_BODY:
                     if(MenuState.GetMenuItem(param1) == MenuState.MenuItem_SKINCOLOR)
                     {
                        this.ShowSkinColorPanel(param1,param2);
                     }
                     else
                     {
                        this.ShowBodyModPanel(param1,param2);
                     }
                     break;
                  case MenuState.MenuSection_HEAD:
                  case MenuState.MenuSection_HAIR:
                     this.ShowFaceUI(param1,param2);
               }
               break;
            case MenuState.MenuMode_CLOTHING:
            case MenuState.MenuMode_ACCESSORIES:
               switch(param1)
               {
                  case MenuState.CLOTHING_BODYSCAR:
                  case MenuState.CLOTHING_BODYDETAILS:
                  case MenuState.CLOTHING_BODY_TATTOOS:
                  case MenuState.CLOTHING_BODY_MEDICAL:
                  case MenuState.CLOTHING_BODY_BODYHAIR_ARM:
                  case MenuState.CLOTHING_BODY_BODYHAIR_LEG:
                  case MenuState.CLOTHING_BODY_BODYHAIR_TORSOFRONT:
                  case MenuState.CLOTHING_BODY_BODYHAIR_TORSOBACK:
                     CASStateData.TattooMode = true;
                     this.HandleSwitchTutorialTipControlEnum(TutorialTipUIElement.CAS_TATTOO_PANEL);
                     break;
                  case MenuState.CLOTHING_FACE_TEETH:
                     CommunicationManager.CallGameService("ShowTeeth",true);
               }
               if(_loc4_ != MenuState.MenuType_MENU)
               {
                  if(param1 == MenuState.CLOTHING_LOOKS)
                  {
                     this.HideClothingPanel();
                     this.ShowLooksPanel();
                  }
                  else
                  {
                     this.ShowClothingPanel(param1,param2);
                  }
               }
               if(MenuState.ShouldZoomHands(param1) && param3)
               {
                  CommunicationManager.CallGameService("CasSetZoomState",{
                     "zoomState":CASMode.HANDS,
                     "playAudio":true
                  });
               }
               else if((MenuState.IsTattoo(param1) || Boolean(CASConfiguration.IsTattooOnlyMode)) && param3)
               {
                  _loc8_ = this.GetFocusableBodyTypePanel();
                  CommunicationManager.CallGameService("CasSetZoomState",{
                     "zoomState":CASMode.BODY_PART,
                     "bodyType":_loc8_.GetSelected(),
                     "playAudio":true
                  });
               }
               this.HandleContextMenuUpdate(this.mContextMenuState);
               break;
            case MenuState.MenuMode_FEATURED:
               if(param1 == MenuState.FEATURED_FACE_PRESETS)
               {
                  CommunicationManager.CallGameService("ShowTeeth",true);
                  this.ShowFeaturedFaceLookPanel(param1,param2);
               }
         }
      }
      
      protected function HandleShowCursorAttachment(param1:Object) : void
      {
         var _loc2_:uint = this.mCurrCursorType;
         var _loc3_:uint = uint(param1["cursor_type"]);
         if(Boolean(SystemUtils.UsingController) && !(NavManager.Instance.CurrentFocusable is CASCenterMainAdapter) && _loc3_ != CursorIconType.NONE)
         {
            return;
         }
         var _loc4_:MovieClip = this.mcCursorAttachment;
         if(_loc3_ != this.mCurrCursorType)
         {
            this.mCurrCursorType = _loc3_;
            switch(_loc3_)
            {
               case CursorIconType.FREETRANSFORM:
                  _loc4_.gotoAndPlay("freetransform");
                  break;
               case CursorIconType.HORIZONTAL:
                  _loc4_.gotoAndPlay("horizontal");
                  break;
               case CursorIconType.VERTICAL:
                  _loc4_.gotoAndPlay("vertical");
                  break;
               case CursorIconType.SCALE:
                  _loc4_.gotoAndPlay("scale");
                  break;
               case CursorIconType.ROTATE:
                  _loc4_.gotoAndPlay("rotate");
                  break;
               case CursorIconType.FREEROTATE:
                  _loc4_.gotoAndPlay("freerotate");
                  break;
               case CursorIconType.SIMSELECT:
               case CursorIconType.NONE:
               default:
                  _loc4_.visible = false;
                  this.StopMouseDragging(_loc2_);
                  return;
            }
            _loc4_.visible = true;
            if(SystemUtils.UsingConsoleInputMode)
            {
               _loc4_.scaleX = _loc4_.scaleY = 1 / SystemUtils.UIScale * SystemUtils.VirtualCursorScale;
            }
            else
            {
               _loc4_.scaleX = _loc4_.scaleY = SystemUtils.VirtualCursorScale;
            }
         }
         var _loc5_:Point = new Point(param1["RubberBandDistX"],param1["RubberBandDistY"]);
         this.UpdateDMBoundaryIndicators(_loc5_);
         var _loc6_:Boolean = param1["dragging"] as Boolean;
         if(_loc6_)
         {
            this.StartMouseDragging(param1);
         }
         else
         {
            this.StopMouseDragging(_loc2_);
         }
      }
      
      protected function StartMouseDragging(param1:Object) : void
      {
         var _loc2_:uint = 0;
         var _loc3_:MovieClip = null;
         var _loc4_:Boolean = false;
         var _loc5_:Boolean = false;
         if(!this.mIsMouseDragging)
         {
            _loc2_ = uint(param1["cursor_type"]);
            _loc3_ = this.mcCursorAttachment;
            _loc4_ = this.mcDetailedEditModePanel.IsActive();
            _loc3_.mcMainCursor.visible = true;
            this.mIsMouseDragging = true;
            if(_loc2_ == CursorIconType.FREEROTATE)
            {
               _loc3_.mcMainCursor.visible = false;
               CommunicationManager.CallGameService("BindDisplayObject",{
                  "displayObject":this.mcCursorAttachment,
                  "attachPoint":"MOUSE",
                  "lockX":true,
                  "lockY":true
               });
               this.mbMouseLocked = true;
            }
            else
            {
               _loc5_ = Boolean(this.mcDetailedEditModePanel.visible);
               if(_loc5_)
               {
                  CommunicationManager.SendUIMessage("CASHidePersonalityAndGeneticsPanels",null);
               }
            }
            if(!_loc4_)
            {
               CommunicationManager.SendUIMessage("CASContextMenuSetBackgroundMode",true);
            }
         }
      }
      
      protected function StopMouseDragging(param1:uint) : void
      {
         if(this.mIsMouseDragging)
         {
            this.mcCursorAttachment.mcMainCursor.visible = false;
            this.mIsMouseDragging = false;
            if(!this.mcDetailedEditModePanel.IsActive())
            {
               CommunicationManager.SendUIMessage("CASContextMenuSetBackgroundMode",false);
            }
            if(this.mbMouseLocked)
            {
               CommunicationManager.CallGameService("BindDisplayObject",{
                  "displayObject":this.mcCursorAttachment,
                  "attachPoint":"MOUSE"
               });
               this.mbMouseLocked = false;
            }
         }
      }
      
      protected function UpdateDMBoundaryIndicators(param1:Point) : void
      {
         this.ShowDMBoundaryIndicators(CASCustomizerTunables.ARROW_AXIS_X,param1.x);
         this.ShowDMBoundaryIndicators(CASCustomizerTunables.ARROW_AXIS_Y,param1.y);
      }
      
      protected function HideDMBoundaryIndicators() : void
      {
         this.ShowDMBoundaryIndicators(CASCustomizerTunables.ARROW_AXIS_X,0);
         this.ShowDMBoundaryIndicators(CASCustomizerTunables.ARROW_AXIS_Y,0);
      }
      
      protected function ShowDMBoundaryIndicators(param1:uint, param2:Number) : void
      {
         var _loc3_:Number = 2;
         var _loc4_:Boolean = false;
         var _loc5_:Boolean = false;
         var _loc6_:Boolean = false;
         var _loc7_:Boolean = false;
         var _loc8_:Boolean = this.mCurrCursorType == CursorIconType.FREETRANSFORM || this.mCurrCursorType == CursorIconType.HORIZONTAL;
         var _loc9_:Boolean = this.mCurrCursorType == CursorIconType.FREETRANSFORM || this.mCurrCursorType == CursorIconType.VERTICAL;
         var _loc10_:Boolean = param1 == CASCustomizerTunables.ARROW_AXIS_X && _loc8_ || param1 == CASCustomizerTunables.ARROW_AXIS_Y && _loc9_;
         if(param2 > 0 && param2 <= _loc3_)
         {
            _loc5_ = _loc10_;
         }
         else if(param2 >= -_loc3_ && param2 < 0)
         {
            _loc4_ = _loc10_;
         }
         else if(param2 > _loc3_)
         {
            _loc7_ = _loc10_;
         }
         else if(param2 < -_loc3_)
         {
            _loc6_ = _loc10_;
         }
         var _loc11_:MovieClip = this.mcCursorAttachment;
         switch(param1)
         {
            case CASCustomizerTunables.ARROW_AXIS_Y:
               _loc11_.mcEdgeIndicatorTop.visible = _loc4_;
               _loc11_.mcRubberBandIndicatorTop.visible = _loc6_;
               _loc11_.mcEdgeIndicatorBottom.visible = _loc5_;
               _loc11_.mcRubberBandIndicatorBottom.visible = _loc7_;
               break;
            case CASCustomizerTunables.ARROW_AXIS_X:
               _loc11_.mcEdgeIndicatorRight.visible = _loc5_;
               _loc11_.mcRubberBandIndicatorRight.visible = _loc7_;
               _loc11_.mcEdgeIndicatorLeft.visible = _loc4_;
               _loc11_.mcRubberBandIndicatorLeft.visible = _loc6_;
         }
      }
      
      protected function HandleSetSimInfo(param1:SimInfo) : void
      {
         var _loc2_:Boolean = Boolean(CommunicationManager.CallGameService("CasIsForcedFullEditingEnabled",null,true));
         this.mbFullEditingEnabled = _loc2_ || Boolean(param1.SimIsNew);
         this.mCurrSimInfo = param1;
         CommunicationManager.SendUIMessage("CASContextMenuSetSimInfo",param1);
         this.mcBodyModSliderPanel.enabled = !param1.IsOccultAlternateForm();
         this.mcBodyModSliderPanel.RefreshSimAge({"simAge":param1.age});
         this.HandleContextMenuUpdate(this.mContextMenuState);
         var _loc3_:TutorialTipExtension = TutorialTipExtension.Get(this.mcClothingPanel);
         _loc3_.ControlEnum = TutorialTipUIElement.CAS_CLOTHING_PANEL;
         if(Boolean(CASConfiguration.IsTattooOnlyMode) && CASStateData.sCASSubState != CASSubStates.PETPAINTING)
         {
            this.HandleContextMenuSetMenuState({
               "menuState":MenuState.CLOTHING_BODY_TATTOOS,
               "setZoomState":true
            });
            _loc3_.ControlEnum = TutorialTipUIElement.CAS_TATTOO_PANEL;
            AddMessageListener("SimModelSet",this.HandleSimModelSet);
         }
      }
      
      protected function HandleSwitchTutorialTipControlEnum(param1:String) : void
      {
         var _loc2_:TutorialTipExtension = TutorialTipExtension.Get(this.mcClothingPanel);
         _loc2_.MarkVisibility(false);
         _loc2_.ControlEnum = param1;
         _loc2_.MarkVisibility(true);
      }
      
      protected function ShowBodyModPanel(param1:int, param2:Boolean = false) : void
      {
         this.RefreshAndShowPanel(this.mcBodyModPanel,param1,param2);
         CommunicationManager.SendUIMessage("CASHidePersonalityAndGeneticsPanels",null);
      }
      
      protected function ShowSkinColorPanel(param1:int, param2:Boolean = false) : void
      {
         this.RefreshAndShowPanel(this.mcSkinColorPanel,param1,param2);
         CommunicationManager.SendUIMessage("CASHidePersonalityAndGeneticsPanels",null);
      }
      
      protected function ShowFeaturedFaceLookPanel(param1:int, param2:Boolean = false) : void
      {
         this.RefreshFilterPane(this.mcFeaturedFaceLookPanel,param1,param2);
         this.RefreshAndShowPanel(this.mcFeaturedFaceLookPanel,param1,param2);
      }
      
      protected function ShowGenericCatalogPanel(param1:int, param2:int, param3:Boolean = false) : void
      {
         this.mcGenericCatalogPanel.CreatePanel(param2);
         this.RefreshFilterPane(this.mcGenericCatalogPanel,param1,param3);
         this.RefreshAndShowPanel(this.mcGenericCatalogPanel,param1,param3);
      }
      
      protected function ShowFaceUI(param1:int, param2:Boolean = false) : void
      {
         if(Boolean(Species.IsPet(this.mCurrSimInfo.speciesType)) && (param1 == MenuState.PROFILE_HEAD_MOUTH || param1 == MenuState.PROFILE_HEAD_JAW))
         {
            return;
         }
         if(!this.mcDetailedEditModePanel.IsActive())
         {
            this.RefreshAndShowPanel(this.mcFaceModPanel,param1,param2);
            if(param1 != MenuState.PROFILE_HEAD_WHOLE_HEADS && (this.mbGameDrivenStateChange || param1 != MenuState.PROFILE_HEAD_EARS || this.mCurrSimInfo.occultType != OccultTypes.OCCULT_FAIRY || !this.mCurrSimInfo.IsOccultAlternateForm()))
            {
               CommunicationManager.SendUIMessage("CASContextMenuSetFaceMode",null);
            }
         }
      }
      
      protected function ShowClothingPanel(param1:int, param2:Boolean = false) : void
      {
         if(!CASConfiguration.IsFashionMode && MenuState.SupportsPlanOutfit(param1))
         {
            CommunicationManager.SendUIMessage("CASSetPlanOutfitVisible",{
               "visible":true,
               "width":CASCustomizerTunables.CATALOG_WIDTH,
               "skipAnim":param2
            });
            this.mcClothingPanel.DisableTopEndCap();
            this.mcClothingPanel.y = CASCustomizerTunables.PANEL_TOP_MARGIN;
            if(Boolean(SystemUtils.UsingController) && Boolean(Species.IsPet(this.mCurrSimInfo.speciesType)))
            {
               this.mcClothingPanel.y = CASCustomizerTunables.CONSOLE_PETS_PANEL_TOP_MARGIN;
            }
         }
         else
         {
            this.mcClothingPanel.EnableTopEndCap();
            this.mcClothingPanel.y = CASCustomizerTunables.PANEL_TOP_MARGIN_WITHOUT_OUTFIT;
         }
         this.AlignComponents();
         if(MenuState.ClothingMenuStatePaintableBodyType(param1) != CASBodyType.NONE)
         {
            this.mcClothingPanel.ShowPaintingPanel();
         }
         this.RefreshFilterPane(this.mcClothingPanel,param1,param2);
         this.RefreshAndShowPanel(this.mcClothingPanel,param1,param2);
         TutorialTipExtension.Get(this.mcClothingPanel).MarkVisibility(true);
      }
      
      protected function ShowLooksPanel() : void
      {
         CommunicationManager.SendUIMessage("CASSetFeatureLooksVisible",true);
      }
      
      protected function HideLooksPanel() : void
      {
         CommunicationManager.SendUIMessage("CASSetFeatureLooksVisible",false);
      }
      
      protected function HideClothingPanel() : void
      {
         if(!this.mcClothingPanel.IsVisible())
         {
            return;
         }
         this.mcClothingPanel.HidePaintingPanel();
         this.HidePanel(this.mcClothingPanel);
         TutorialTipExtension.Get(this.mcClothingPanel).MarkVisibility(false);
         CommunicationManager.SendUIMessage("CASSetPlanOutfitVisible",{"visible":false});
      }
      
      protected function HideFeaturedFaceLookPanel() : void
      {
         if(!this.mcFeaturedFaceLookPanel.IsVisible())
         {
            return;
         }
         this.HidePanel(this.mcFeaturedFaceLookPanel);
      }
      
      protected function HandleContextMenuSetMenuState(param1:Object) : void
      {
         var _loc2_:Boolean = "setZoomState" in param1 ? param1["setZoomState"] as Boolean : true;
         this.SetState(param1["menuState"] as int,true,param1["skipAnim"] as Boolean,_loc2_);
      }
      
      protected function HandleMenuStateChange(param1:int) : void
      {
         this.mbGameDrivenStateChange = true;
         this.SetState(param1,false);
         this.mbGameDrivenStateChange = false;
      }
      
      protected function HandleHideRequest() : void
      {
         CommunicationManager.SendUIMessage("CASContextMenuHide",null);
         this.SetMenuState(MenuState.NONE,!CASConfiguration.IsTattooOnlyMode);
         this.HidePanel(this.mcBodyModSliderPanel);
         this.HidePanel(this.mcDetailedEditModePanel);
         if(!CASConfiguration.IsTattooOnlyMode && (this.mCurrSimInfo.occultType != OccultTypes.OCCULT_FAIRY || CASStateData.sCASSubState != CASSubStates.PETPAINTING))
         {
            this.HidePanel(this.mcGhostToggle);
         }
         if(CASStateData.sCASSubState != CASSubStates.PETPAINTING)
         {
            this.HidePanel(this.mcWingToggle);
         }
         if(this.mcDetailedEditModePanel.IsActive())
         {
            this.mcDetailedEditModePanel.ToggleAdvancedMode();
         }
         TutorialTipExtension.Get(this.mcClothingPanel).MarkVisibility(false);
      }
      
      protected function SetMenuState(param1:int, param2:Boolean = true) : void
      {
         this.mForceFilterPaneRefresh = true;
         this.SetState(param1,true,false,param2);
      }
      
      public function HighlightSelectedItem() : void
      {
         var _loc1_:int = 0;
         if(this.mInputAdapter)
         {
            _loc1_ = this.mCurrentPanel.GetFirstSelectedProductIndex();
            if(_loc1_ == -1)
            {
               _loc1_ = 0;
            }
            this.mInputAdapter.SetHighlightedIndex(_loc1_,false,false);
         }
      }
      
      protected function ShowPanel(param1:DisplayObject, param2:Boolean = false) : void
      {
         var _loc4_:CatalogPanel = null;
         var _loc5_:Tween = null;
         var _loc3_:GUIComponent = param1 as GUIComponent;
         if(param1 is CatalogPanel)
         {
            if(Boolean(SystemUtils.UsingController) && Boolean(this.mCurrentPanel) && Boolean(this.mCurrentPanel.mcFilterPane))
            {
               this.mCurrentPanel.mcFilterPane.removeEventListener(GenericEvent.CHANGE,this.HighlightSelectedItem);
            }
            _loc4_ = param1 as CatalogPanel;
            this.mCurrentPanel = _loc4_;
            _loc4_.SetVisible(true);
            if(this.mbGamepadWaitingForCurrentPanel)
            {
               this.SetupAdapterWithCurrentPanel();
            }
            if(Boolean(SystemUtils.UsingController) && Boolean(this.mCurrentPanel) && Boolean(this.mCurrentPanel.mcFilterPane))
            {
               this.mCurrentPanel.mcFilterPane.addEventListener(GenericEvent.CHANGE,this.HighlightSelectedItem);
            }
         }
         else if(!param1.visible || Boolean(_loc3_ && _loc3_.IsAnimatingOut) && Boolean(param2))
         {
            if(param2)
            {
               param1.alpha = 0;
               param1.visible = true;
               _loc5_ = Tween.QuickAnimation(Animation.FADE_IN,CASCustomizerTunables.PANEL_FADE_IN_DELAY,param1);
               _loc5_.addEventListener(TweenEvent.TWEEN_COMPLETE,this.OnPanelFadeInComplete,false,0,true);
               _loc5_.Start();
               if(_loc3_)
               {
                  _loc3_.IsAnimatingIn = true;
               }
               this.mCASTelemetry.StartTimedTelemeter();
            }
            else
            {
               param1.visible = true;
            }
         }
      }
      
      protected function HidePanel(param1:DisplayObject, param2:Boolean = false) : void
      {
         var _loc4_:CatalogPanel = null;
         var _loc5_:Tween = null;
         var _loc3_:GUIComponent = param1 as GUIComponent;
         if(param1 is CatalogPanel)
         {
            if(Boolean(SystemUtils.UsingController) && Boolean(this.mCurrentPanel) && Boolean(this.mCurrentPanel.mcFilterPane))
            {
               this.mCurrentPanel.mcFilterPane.removeEventListener(GenericEvent.CHANGE,this.HighlightSelectedItem);
            }
            _loc4_ = param1 as CatalogPanel;
            _loc4_.SetVisible(false);
            this.mCurrentPanel = null;
         }
         else if(param1.visible || Boolean(_loc3_ && _loc3_.IsAnimatingIn) && Boolean(param2))
         {
            if(param2)
            {
               _loc5_ = Tween.QuickAnimation(Animation.FADE_OUT,CASCustomizerTunables.PANEL_FADE_OUT_DELAY,param1);
               _loc5_.addEventListener(TweenEvent.TWEEN_COMPLETE,this.OnPanelFadeOutComplete,false,0,true);
               _loc5_.Start();
               if(_loc3_)
               {
                  _loc3_.IsAnimatingOut = true;
               }
               this.mCASTelemetry.EndTimedTelemeter();
            }
            else
            {
               param1.visible = false;
            }
         }
      }
      
      protected function RefreshAndShowPanel(param1:CatalogPanel, param2:int, param3:Boolean = false) : void
      {
         this.RefreshPanel(param1,param2);
         this.HideAllPanels(param1);
         if(param3)
         {
            param1.SkipAnimation();
         }
         this.ShowPanel(param1);
      }
      
      protected function RefreshPanel(param1:DisplayObject, param2:int) : void
      {
         var _loc3_:CatalogPanel = null;
         if(param1 is CatalogPanel)
         {
            _loc3_ = param1 as CatalogPanel;
            _loc3_.Refresh(param2);
         }
      }
      
      protected function HideAllPanels(param1:DisplayObject = null) : void
      {
         var _loc2_:CatalogPanel = null;
         for each(_loc2_ in this.mPanels)
         {
            if(_loc2_ != param1)
            {
               this.HidePanel(_loc2_);
            }
         }
      }
      
      protected function OnPanelFadeOutComplete(param1:TweenEvent) : void
      {
         var _loc2_:Tween = param1.currentTarget as Tween;
         (_loc2_.Target as DisplayObject).visible = false;
         var _loc3_:GUIComponent = _loc2_.Target as GUIComponent;
         if(_loc3_)
         {
            _loc3_.IsAnimatingOut = false;
         }
      }
      
      protected function OnPanelFadeInComplete(param1:TweenEvent) : void
      {
         var _loc2_:Tween = param1.currentTarget as Tween;
         (_loc2_.Target as DisplayObject).visible = true;
         var _loc3_:GUIComponent = _loc2_.Target as GUIComponent;
         if(_loc3_)
         {
            _loc3_.IsAnimatingIn = false;
         }
      }
      
      protected function HandleBackOutUI(param1:Object) : void
      {
         if(this.mCurrentPanel)
         {
            if(this.mCurrentPanel.HandleBackOutUI())
            {
               return;
            }
         }
         CommunicationManager.SendUIMessage("CASContextMenuBackout");
      }
      
      protected function HandleUndoEnabled(param1:Boolean) : void
      {
         if(param1)
         {
            sHasPendingEdits = true;
         }
      }
      
      protected function HandleToggleFeaturedLooksMode(param1:Object) : void
      {
         if(this.mCurrState == MenuState.CLOTHING_LOOKS)
         {
            this.SetState(MenuState.NONE,true);
         }
         else
         {
            this.HandleBackOutUI(null);
            this.SetState(MenuState.CLOTHING_LOOKS,true);
         }
      }
      
      protected function HandleContextMenuUpdate(param1:int) : void
      {
         this.mContextMenuState = param1;
         if(param1 == CASContextMenuState.BODY && (this.mbFullEditingEnabled || Boolean(CASConfiguration.IsMannequinMode) && !CASConfiguration.IsUniformMode) && !(Boolean(Species.IsPet(this.mCurrSimInfo.speciesType)) && Boolean(SimAgeTypes.IsChildOrYounger(this.mCurrSimInfo.age))) && !MenuState.ShouldZoomHands(this.mNextState))
         {
            this.ShowPanel(this.mcBodyModSliderPanel,true);
         }
         else
         {
            this.HidePanel(this.mcBodyModSliderPanel,true);
         }
         if(param1 == CASContextMenuState.HEAD && (this.mbFullEditingEnabled || Boolean(CASConfiguration.IsAlienMode) || Boolean(CASConfiguration.IsEditGenderMode) || Boolean(CASConfiguration.IsSimCustomizationMode)))
         {
            this.ShowPanel(this.mcDetailedEditModePanel,true);
         }
         else
         {
            this.HidePanel(this.mcDetailedEditModePanel,true);
         }
         var _loc2_:int = CommunicationManager.CallGameService("CasGetPaintMode") as int;
         if(!SystemUtils.UsingController && (param1 == CASContextMenuState.BODY || param1 == CASContextMenuState.HEAD || CASStateData.sCASSubState == CASSubStates.PETPAINTING && (_loc2_ == CASConfiguration.PAINTMODE_TATTOO || _loc2_ == CASConfiguration.PAINTMODE_WING) || Boolean(CASConfiguration.IsTattooOnlyMode)))
         {
            if(this.mCurrSimInfo.isGhost)
            {
               this.PositionGhostToggle();
               this.ShowPanel(this.mcGhostToggle);
               this.mcGhostToggle.mCurrState = this.mContextMenuState;
            }
            else
            {
               this.HidePanel(this.mcGhostToggle);
            }
            if(this.mCurrSimInfo.occultType == OccultTypes.OCCULT_FAIRY && Boolean(this.mCurrSimInfo.IsOccultAlternateForm))
            {
               this.PositionWingToggle();
               this.ShowPanel(this.mcWingToggle);
            }
            else
            {
               this.HidePanel(this.mcWingToggle);
            }
         }
         else
         {
            this.HidePanel(this.mcGhostToggle);
            this.HidePanel(this.mcWingToggle);
         }
      }
      
      protected function PositionGhostToggle() : void
      {
         if(this.mContextMenuState == CASContextMenuState.BODY)
         {
            this.mcGhostToggle.y = this.mcBodyModSliderPanel.y + this.mcBodyModSliderPanel.height / 2 + CASCustomizerTunables.GHOST_TOGGLE_PADDING;
         }
         else
         {
            this.mcGhostToggle.y = this.mcDetailedEditModePanel.y + this.mcDetailedEditModePanel.height + CASCustomizerTunables.GHOST_TOGGLE_PADDING;
         }
      }
      
      protected function PositionWingToggle() : void
      {
         if(this.mContextMenuState == CASContextMenuState.BODY)
         {
            this.mcWingToggle.y = this.mcBodyModSliderPanel.y + this.mcBodyModSliderPanel.height / 2 + CASCustomizerTunables.WING_TOGGLE_PADDING;
         }
         else
         {
            this.mcWingToggle.y = this.mcDetailedEditModePanel.y + this.mcDetailedEditModePanel.height + CASCustomizerTunables.WING_TOGGLE_PADDING;
         }
      }
      
      protected function BeforeShowingExitMenu() : Boolean
      {
         this.HandleHideCursorAttachment();
         return true;
      }
      
      public function HandleHideCursorAttachment() : void
      {
         var _loc1_:Object = new Object();
         _loc1_["cursor_type"] = CursorIconType.NONE;
         this.HandleShowCursorAttachment(_loc1_);
      }
      
      protected function HandleMouseEnterLeaveUI(param1:Object = null) : void
      {
         if(param1 == true)
         {
            this.mCurrCursorType = CursorIconType.NONE;
            this.mcCursorAttachment.visible = false;
         }
      }
      
      protected function RefreshFilterPane(param1:CatalogPanel, param2:int, param3:Boolean) : void
      {
         var _loc4_:Boolean = MenuState.SupportsFilterPane(param2,this.mCurrSimInfo);
         var _loc5_:CASFilterPane = param1.mcFilterPane;
         if(!_loc5_)
         {
            return;
         }
         _loc5_.Refresh(param2,this.mForceFilterPaneRefresh);
         this.mForceFilterPaneRefresh = false;
         if(_loc4_)
         {
            _loc5_.SetPanelHeight(CASFilterPaneTunables.FILTER_PANEL_HEIGHT);
            _loc5_.Show();
         }
         else
         {
            _loc5_.Hide();
         }
      }
      
      protected function InitGamepad() : void
      {
         var topSectionLegendKey:LocKey;
         var tabLeft:InputAction;
         var tabRight:InputAction;
         AddMessageListener("OpenFilterPanel",this.HandleOpenFilterPanel);
         AddMessageListener("GamepadRandomizeCustomizer",this.GamepadRandomize);
         this.mInputAdapter = new GridInputAdapter(null);
         this.mInputAdapter.SetUseDefaultConfirm(false);
         this.mInputAdapter.SetUseDPadLeaveEdgeRowSkipBehavior(true);
         this.mInputAdapter.SetDPadLeaveEdgeNumberOfRowsToSkip(CASCustomizerTunables.CATALOG_CONTROLLER_DPAD_X_EDGE_SKIP_ROWS);
         this.mInputAdapter.OnConfirmCall(this.OnGamepadConfirm);
         if(!CASConfiguration.IsTattooOnlyMode)
         {
            this.mInputAdapter.OnBackCall(this.OnGamepadBack);
         }
         this.mInputAdapter.OnEnteredCall(this.HandleMainInputEntered);
         this.mInputAdapter.OnExitedCall(this.HandleMainInputExited);
         this.mInputAdapter.OnLeaveCall(this.OnMainAdapterLeave);
         topSectionLegendKey = CASStateData.TattooMode ? KeysConsole.CAS_ENTER_TATTOO_LAYERS : KeysConsole.CAS_ENTER_OUTFITS_AND_FILTERS;
         this.mGamepadTopSectionAction = InputAction.WhenTriggered(InputTrigger.FromActionCode(CASActionCodes.ENTER_PLAN_OUTFITS)).CallFunction(this.GamepadTopSectionActionTriggered).SetValidCheck(this.CanEnterTopSection).SetLegendKey(topSectionLegendKey);
         this.mGamepadRandomizeAction = InputAction.WhenTriggered(InputTrigger.FromActionCode(CASActionCodes.RANDOMIZE)).CallFunction(this.GamepadRandomize).SetValidQuickLegendCheck(function():Boolean
         {
            return false;
         }).SetLegendKey(KeysConsole.CAS_RANDOMIZE);
         this.mInputAdapter.AddInputActions([this.mGamepadTopSectionAction,CASSharedActions.openFilterAction]);
         this.mFilterBubbleAdapter = new BidirectionalGroupAdapter();
         this.mFilterBubbleAdapter.OnBackCall(this.OnGamepadBack).OnLeaveCall(this.HandleLeaveFilterPane).OnEnteredCall(this.HandleFilterAdapterEntered).OnExitedCall(this.HandleFilterAdapterExited);
         this.mFilterBubbleAdapter.AddInputAction(CASSharedActions.openFilterAction);
         tabLeft = InputAction.WhenTriggered(InputTrigger.FromActionCode(ActionCodes.TAB_LEFT)).AllowWhileModalOpen(true).SetValidCheck(this.CanOverrideTabs).DispatchUIMessage("CASTabBodyType",-1);
         tabRight = InputAction.WhenTriggered(InputTrigger.FromActionCode(ActionCodes.TAB_RIGHT)).AllowWhileModalOpen(true).SetValidCheck(this.CanOverrideTabs).DispatchUIMessage("CASTabBodyType",1);
         this.mInputAdapter.AddInputActions([tabLeft,tabRight]);
      }
      
      protected function OnGamepadConfirm() : void
      {
         var _loc1_:DisplayObject = null;
         var _loc2_:CASClothingPanelCellViewMain = null;
         if(this.mInputAdapter)
         {
            _loc1_ = this.mInputAdapter.GetHighlightedObject();
            if(_loc1_)
            {
               _loc2_ = _loc1_ as CASClothingPanelCellViewMain;
               if(Boolean(_loc2_ && _loc2_.Selected) && Boolean(_loc2_.btnVariationStackContainer.visible) && !(this.mCurrSimInfo.occultType == OccultTypes.OCCULT_MERMAID && MenuState.GetMenuItem(this.mCurrState) == MenuState.MenuItem_TAIL))
               {
                  _loc1_.dispatchEvent(new CASCatalogEvent(CASCatalogEvent.REMOVE_BUTTON_CLICKED,true,false));
                  if(this.mcClothingPanel.RemoveFailed)
                  {
                     this.GamepadOpenVariations();
                  }
               }
               else if(!this.GamepadOpenVariations())
               {
                  this.mInputAdapter.ConfirmHighlight();
               }
            }
         }
         this.mcClothingPanel.RemoveFailed = false;
      }
      
      protected function OnGamepadBack() : void
      {
         if(CASConfiguration.IsTattooOnlyMode)
         {
            return;
         }
         this.SetMenuState(MenuState.NONE);
         NavManager.Instance.FocusBack();
      }
      
      protected function HandleMainInputEntered() : void
      {
         var _loc1_:Boolean = this.mCurrentPanel != null && this.mCurrentPanel.SupportsRandomization;
         if(_loc1_ && Boolean(this.mInputAdapter.IsCurrentlyEntered()))
         {
            if(!this.mbGamepadRandomizeEnabled)
            {
               InputActionManager.RegisterAction(this.mGamepadRandomizeAction);
               this.mbGamepadRandomizeEnabled = true;
            }
         }
         else if(this.mbGamepadRandomizeEnabled)
         {
            this.RemoveRandomizeAction();
         }
         CASSharedActions.openFilterAction.SetValidCheck(this.CanOpenFilterPanel);
      }
      
      protected function HandleMainInputExited() : void
      {
         this.RemoveRandomizeAction();
         CASSharedActions.openFilterAction.SetValidCheck(null);
         CASSharedActions.openFilterAction.SetProvideHint(true);
      }
      
      protected function RemoveRandomizeAction() : void
      {
         InputActionManager.UnregisterAction(this.mGamepadRandomizeAction);
         this.mbGamepadRandomizeEnabled = false;
      }
      
      protected function OnMainAdapterLeave(param1:InputAdapterLeaveEvent) : void
      {
         var _loc2_:uint = uint(param1.GetDirection());
         if(_loc2_ == NavDirection.UP || _loc2_ == NavDirection.LEFT)
         {
            if(this.CanEnterTopSection())
            {
               this.GamepadEnterTopSection(param1);
            }
         }
         else if(_loc2_ == NavDirection.DOWN || _loc2_ == NavDirection.RIGHT)
         {
            if(this.mCurrentPanel is GenericCatalogPanel)
            {
               if(this.mCurrentPanel.Footer)
               {
                  NavManager.Instance.FocusPan(this.mCurrentPanel.Footer,param1.CreateEnterParams());
               }
            }
         }
      }
      
      protected function HandleFilterAdapterEntered() : void
      {
         CASSharedActions.openFilterAction.SetValidCheck(this.CanOpenFilterPanel);
      }
      
      protected function HandleFilterAdapterExited() : void
      {
         CASSharedActions.openFilterAction.SetValidCheck(null);
         CASSharedActions.openFilterAction.SetProvideHint(true);
      }
      
      protected function GamepadEnterTopSection(param1:InputAdapterLeaveEvent = null) : void
      {
         var _loc6_:uint = 0;
         var _loc7_:Point = null;
         var _loc8_:EnterParams = null;
         var _loc9_:ColorSwatchPanel = null;
         var _loc10_:SkinToneFilter = null;
         var _loc11_:Boolean = false;
         var _loc2_:HairGrowthPanel = this.GetFocusableHairGrowthPanel();
         if(_loc2_)
         {
            NavManager.Instance.FocusPan(_loc2_,new EnterParams(NavDirection.UP));
            return;
         }
         var _loc3_:CASLayerComponent = this.GetFocusableLayerComponent();
         if(_loc3_)
         {
            _loc6_ = param1 ? uint(param1.GetDirection()) : uint(NavDirection.UP);
            _loc7_ = param1 ? param1.GetFromPosition() : null;
            _loc8_ = new EnterParams(_loc6_,_loc7_,{"bFromInputAction":this.mbFromInputAction});
            NavManager.Instance.FocusPan(_loc3_,_loc8_);
            return;
         }
         var _loc4_:CASBodyTypePanel = this.GetFocusableBodyTypePanel();
         if(_loc4_)
         {
            NavManager.Instance.FocusPan(_loc4_);
            return;
         }
         if(this.mCurrentPanel is ColorSwatchCatalogPanel)
         {
            _loc9_ = (this.mCurrentPanel as ColorSwatchCatalogPanel).mcColorSwatchPanel;
            if(Boolean(_loc9_) && _loc9_.ShouldBeFocusable())
            {
               NavManager.Instance.FocusPan(_loc9_,new EnterParams(NavDirection.UP));
               return;
            }
         }
         if(this.mCurrentPanel is SkinTonePanel)
         {
            _loc10_ = (this.mCurrentPanel as SkinTonePanel).mSkinToneFilter;
            if(_loc10_)
            {
               _loc10_.OnInputEventCall(InputAdapterEvent.LEAVE,this.HandleLeaveFilterPane);
               _loc10_.OnInputEventCall(InputAdapterEvent.BACK,this.OnGamepadBack);
               NavManager.Instance.FocusPan(_loc10_);
               return;
            }
         }
         if(this.mCurrentPanel is ClothingPanel)
         {
            _loc11_ = (this.mCurrentPanel as ClothingPanel).HeaderIsPaintingPane();
            if(_loc11_)
            {
               NavManager.Instance.FocusPan(this.mCurrentPanel.Header);
               return;
            }
         }
         var _loc5_:CASFilterPane = this.mCurrentPanel.mcFilterPane;
         if(Boolean(_loc5_) && Boolean(_loc5_.visible))
         {
            NavManager.Instance.FocusPan(this.mFilterBubbleAdapter);
            return;
         }
         if(this.mCurrentPanel is GenericCatalogPanel)
         {
            if(this.mCurrentPanel.Header)
            {
               NavManager.Instance.FocusPan(this.mCurrentPanel.Header);
               return;
            }
         }
         NavManager.Instance.FocusWidgetForward("CASPlanOutfit");
      }
      
      protected function GamepadTopSectionActionTriggered() : void
      {
         this.mbFromInputAction = true;
         this.GamepadEnterTopSection();
      }
      
      protected function CanEnterTopSection() : Boolean
      {
         var _loc6_:ColorSwatchPanel = null;
         var _loc7_:SkinToneFilter = null;
         var _loc8_:Boolean = false;
         var _loc9_:CASFilterPane = null;
         if(CASStateData.TattooMode)
         {
            CASSharedActions.openFilterAction.SetProvideHint(false);
         }
         var _loc1_:HairGrowthPanel = this.GetFocusableHairGrowthPanel();
         this.mGamepadTopSectionAction.SetLegendKey(KeysConsole.CAS_ENTER_OUTFITS_AND_FILTERS);
         if(_loc1_)
         {
            return true;
         }
         var _loc2_:ApplyAllPanel = this.GetFocusableApplyAllPanel();
         if(_loc2_)
         {
            return true;
         }
         var _loc3_:CASLayerComponent = this.GetFocusableLayerComponent();
         if(_loc3_)
         {
            this.mGamepadTopSectionAction.SetLegendKey(KeysConsole.CAS_ENTER_TATTOO_LAYERS);
            return true;
         }
         var _loc4_:CASBodyTypePanel = this.GetFocusableBodyTypePanel();
         if(_loc4_)
         {
            return true;
         }
         if(this.mCurrentPanel is ColorSwatchCatalogPanel)
         {
            _loc6_ = (this.mCurrentPanel as ColorSwatchCatalogPanel).mcColorSwatchPanel;
            if(Boolean(_loc6_) && _loc6_.ShouldBeFocusable())
            {
               return true;
            }
         }
         if(this.mCurrentPanel is SkinTonePanel)
         {
            _loc7_ = (this.mCurrentPanel as SkinTonePanel).mSkinToneFilter;
            if(_loc7_)
            {
               return true;
            }
         }
         if(this.mCurrentPanel is ClothingPanel)
         {
            _loc8_ = (this.mCurrentPanel as ClothingPanel).HeaderIsPaintingPane();
            if(_loc8_)
            {
               return true;
            }
         }
         if(this.mCurrentPanel)
         {
            _loc9_ = this.mCurrentPanel.mcFilterPane;
            if(Boolean(_loc9_) && Boolean(_loc9_.visible))
            {
               return true;
            }
         }
         if(this.mCurrentPanel is GenericCatalogPanel && Boolean(this.mCurrentPanel.Header))
         {
            return true;
         }
         var _loc5_:WidgetBase = LayoutAPI.GetLoadedWidgetByName("CASPlanOutfit");
         return Boolean(_loc5_) && Boolean(_loc5_.IsReadyToEnter());
      }
      
      protected function GamepadOpenVariations() : Boolean
      {
         var _loc5_:ColorSwatchPanel = null;
         var _loc1_:CASClothingPanelCellViewMain = this.mInputAdapter.GetHighlightedObject() as CASClothingPanelCellViewMain;
         if(_loc1_)
         {
            return _loc1_.OpenVariationGrid();
         }
         var _loc2_:CASGenericCatalogVariantCellView = this.mInputAdapter.GetHighlightedObject() as CASGenericCatalogVariantCellView;
         if(_loc2_)
         {
            return _loc2_.OpenVariationGrid();
         }
         var _loc3_:CASBreedCatalogCellView = this.mInputAdapter.GetHighlightedObject() as CASBreedCatalogCellView;
         if(_loc3_)
         {
            return _loc3_.FocusVariants();
         }
         var _loc4_:ColorSwatchPanelCellView = this.mInputAdapter.GetHighlightedObject() as ColorSwatchPanelCellView;
         if(_loc4_)
         {
            _loc5_ = _loc4_.mcColorSwatchPanel;
            _loc5_.OnInputEventCall(InputAdapterEvent.LEAVE,this.HandleLeaveColorSwatchCellView);
            _loc5_.OnInputEventCall(InputAdapterEvent.BACK,NavManager.Instance.FocusBack);
            NavManager.Instance.FocusForward(_loc5_);
            _loc5_.HighlightSelectedItem();
            return true;
         }
         return false;
      }
      
      protected function GamepadRandomize() : void
      {
         var _loc1_:int = 0;
         if(this.mCurrentPanel.SupportsRandomization)
         {
            this.mCurrentPanel.OnRandomize();
            _loc1_ = this.mCurrentPanel.GetFirstSelectedProductIndex();
            this.mInputAdapter.SetHighlightedIndex(_loc1_);
         }
      }
      
      protected function HandleOpenFilterPanel() : void
      {
         if(Boolean(this.mCurrentPanel) && this.mCurrentPanel.IsVisible())
         {
            NavManager.Instance.ClearHighlight();
            this.mCurrentPanel.mcFilterPane.ConsoleShowFilterPanel();
         }
      }
      
      protected function HandleSimModelSet() : void
      {
         var _loc1_:CASBodyTypePanel = this.GetFocusableBodyTypePanel();
         CommunicationManager.CallGameService("CasSetZoomState",{
            "zoomState":CASMode.BODY_PART,
            "bodyType":_loc1_.GetSelected(),
            "playAudio":true
         });
         RemoveMessageListener("SimModelSet",this.HandleSimModelSet);
      }
      
      protected function CanOpenFilterPanel() : Boolean
      {
         return this.mCurrentPanel && this.mCurrentPanel.IsVisible() && Boolean(this.mCurrentPanel.mcFilterPane) && Boolean(this.mCurrentPanel.mcFilterPane.visible);
      }
      
      protected function CanOverrideTabs() : Boolean
      {
         return MenuState.SupportsBodyTypeFilter(this.mCurrState);
      }
      
      protected function HandleGamepadTabThroughOutfits() : void
      {
         this.mResetInputAdapterHighlight = !CASConfiguration.IsFashionMode && MenuState.SupportsPlanOutfit(this.mCurrState);
         if(this.mResetInputAdapterHighlight)
         {
            this.SetupAdapterWithCurrentPanel();
         }
      }
      
      protected function HandleLeaveFilterPane(param1:InputAdapterLeaveEvent) : void
      {
         var _loc3_:ColorSwatchPanel = null;
         var _loc4_:ApplyAllPanel = null;
         var _loc2_:uint = uint(param1.GetDirection());
         if(_loc2_ == NavDirection.DOWN)
         {
            if(this.mCurrentPanel is ColorSwatchCatalogPanel)
            {
               _loc3_ = (this.mCurrentPanel as ColorSwatchCatalogPanel).mcColorSwatchPanel;
               if(Boolean(_loc3_) && _loc3_.ShouldBeFocusable())
               {
                  NavManager.Instance.FocusPan(_loc3_,param1.CreateEnterParams());
                  return;
               }
            }
            if(this.mInputAdapter.GetVisibleObjects().length)
            {
               NavManager.Instance.FocusPan(this.mInputAdapter);
               return;
            }
         }
         else if(_loc2_ == NavDirection.UP)
         {
            if(this.mCurrentPanel is GenericCatalogPanel)
            {
               if(this.mCurrentPanel.Header)
               {
                  NavManager.Instance.FocusPan(this.mCurrentPanel.Header,param1.CreateEnterParams());
                  return;
               }
            }
            if(!CASConfiguration.IsFashionMode && MenuState.SupportsPlanOutfit(this.mCurrState))
            {
               NavManager.Instance.FocusWidgetForward("CASPlanOutfit");
            }
         }
         else if(_loc2_ == NavDirection.LEFT)
         {
            _loc4_ = this.GetFocusableApplyAllPanel();
            if(_loc4_)
            {
               NavManager.Instance.FocusPan(_loc4_,param1.CreateEnterParams());
               return;
            }
         }
         NavManager.Instance.FocusWidgetPan(param1.GetDirection(),param1.GetFromPosition());
      }
      
      protected function HandleLeaveHairGrowth(param1:InputAdapterLeaveEvent) : void
      {
         var _loc2_:ColorSwatchPanel = null;
         var _loc3_:CASFilterPane = null;
         if(param1.GetDirection() == NavDirection.UP)
         {
            _loc2_ = this.GetFocusableColorSwatch();
            if(_loc2_)
            {
               NavManager.Instance.FocusPan(_loc2_,param1.CreateEnterParams());
               return;
            }
            _loc3_ = this.mCurrentPanel.mcFilterPane;
            if(Boolean(_loc3_) && Boolean(_loc3_.visible))
            {
               NavManager.Instance.FocusPan(this.mFilterBubbleAdapter);
               return;
            }
         }
         NavManager.Instance.FocusPan(this.mInputAdapter);
      }
      
      protected function HandleLeaveLayerComponent(param1:InputAdapterLeaveEvent) : void
      {
         var _loc2_:CASBodyTypePanel = null;
         this.mbFromInputAction = false;
         if(param1.GetDirection() == NavDirection.UP)
         {
            _loc2_ = this.GetFocusableBodyTypePanel();
            if(_loc2_)
            {
               NavManager.Instance.FocusPan(_loc2_,param1.CreateEnterParams());
               return;
            }
         }
         NavManager.Instance.FocusPan(this.mInputAdapter);
      }
      
      protected function HandleLeaveBodyType(param1:InputAdapterLeaveEvent) : void
      {
         var _loc2_:CASLayerComponent = null;
         if(param1.GetDirection() == NavDirection.DOWN)
         {
            _loc2_ = this.GetFocusableLayerComponent();
            if(_loc2_)
            {
               NavManager.Instance.FocusPan(_loc2_,new EnterParams(NavDirection.DOWN));
               return;
            }
            if(this.mInputAdapter.GetVisibleObjects().length)
            {
               NavManager.Instance.FocusPan(this.mInputAdapter);
            }
         }
      }
      
      protected function HandleConfirmBodyType(param1:InputAdapterConfirmEvent) : void
      {
         if(this.mInputAdapter.GetVisibleObjects().length)
         {
            NavManager.Instance.FocusPan(this.mInputAdapter);
         }
      }
      
      protected function HandleLeaveApplyAll(param1:InputAdapterLeaveEvent) : void
      {
         var _loc2_:CASFilterPane = null;
         if(param1.GetDirection() == NavDirection.RIGHT)
         {
            _loc2_ = this.mCurrentPanel.mcFilterPane;
            if(Boolean(_loc2_) && Boolean(_loc2_.visible))
            {
               NavManager.Instance.FocusPan(this.mFilterBubbleAdapter);
               return;
            }
         }
         NavManager.Instance.FocusPan(this.mInputAdapter);
      }
      
      protected function HandleLeaveColorSwatch(param1:InputAdapterLeaveEvent) : void
      {
         var _loc2_:CASFilterPane = null;
         var _loc3_:HairGrowthPanel = null;
         var _loc4_:ApplyAllPanel = null;
         if(param1.GetDirection() == NavDirection.UP)
         {
            _loc2_ = this.mCurrentPanel.mcFilterPane;
            if(Boolean(_loc2_) && Boolean(_loc2_.visible))
            {
               NavManager.Instance.FocusPan(this.mFilterBubbleAdapter);
               return;
            }
         }
         else
         {
            if(param1.GetDirection() == NavDirection.DOWN)
            {
               _loc3_ = this.GetFocusableHairGrowthPanel();
               if(_loc3_)
               {
                  NavManager.Instance.FocusPan(_loc3_,new EnterParams(NavDirection.DOWN));
                  return;
               }
               NavManager.Instance.FocusPan(this.mInputAdapter);
               return;
            }
            if(param1.GetDirection() == NavDirection.LEFT)
            {
               _loc4_ = this.GetFocusableApplyAllPanel();
               if(_loc4_)
               {
                  NavManager.Instance.FocusPan(_loc4_,new EnterParams(NavDirection.LEFT));
                  return;
               }
            }
         }
         NavManager.Instance.FocusWidgetPan(param1.GetDirection(),param1.GetFromPosition());
      }
      
      protected function HandleLeaveColorSwatchCellView(param1:InputAdapterLeaveEvent) : void
      {
         NavManager.Instance.FocusWidgetPan(param1.GetDirection(),param1.GetFromPosition());
      }
      
      override public function IsReadyToEnter(param1:EnterParams = null) : Boolean
      {
         if(Boolean(param1.mArgs) && Boolean(param1.mArgs["EnterLeftSide"]))
         {
            if(Boolean(this.mcBodyModSliderPanel.visible) && Boolean(this.mCurrSimInfo.IsOccultAlternateForm()))
            {
               return false;
            }
            return Boolean(this.mcBodyModSliderPanel.visible) || Boolean(this.mcDetailedEditModePanel.visible);
         }
         if(this.mCurrentPanel)
         {
            return this.mCurrentPanel.IsVisible();
         }
         if(Boolean(param1) && param1.mDirection == NavDirection.BACK)
         {
            return Boolean(this.mcBodyModSliderPanel.visible) || Boolean(this.mcDetailedEditModePanel.visible) || this.mcDetailedEditModePanel.IsActive();
         }
         return false;
      }
      
      override public function Enter(param1:EnterParams = null) : IInputFocusable
      {
         var _loc3_:CASFilterPane = null;
         var _loc4_:ColorSwatchPanel = null;
         var _loc5_:HairGrowthPanel = null;
         var _loc6_:ApplyAllPanel = null;
         var _loc7_:CASBodyTypePanel = null;
         var _loc2_:Boolean = Boolean(param1.mArgs) && Boolean(param1.mArgs["EnterLeftSide"]);
         if(_loc2_)
         {
            if(this.mcBodyModSliderPanel.visible)
            {
               return this.mcBodyModSliderPanel.Enter(param1);
            }
            if(this.mcDetailedEditModePanel.visible)
            {
               return this.mcDetailedEditModePanel.Enter(param1);
            }
         }
         if(Boolean(param1) && param1.mDirection == NavDirection.DOWN)
         {
            _loc3_ = this.mCurrentPanel.mcFilterPane;
            if(Boolean(_loc3_) && Boolean(_loc3_.visible))
            {
               return this.mFilterBubbleAdapter.Enter(param1);
            }
            _loc4_ = this.GetFocusableColorSwatch();
            if(_loc4_)
            {
               return _loc4_.Enter(param1);
            }
            _loc5_ = this.GetFocusableHairGrowthPanel();
            if(_loc5_)
            {
               return _loc5_.Enter(param1);
            }
            _loc6_ = this.GetFocusableApplyAllPanel();
            if(_loc6_)
            {
               return _loc6_.Enter(param1);
            }
         }
         if(this.mCurrentPanel == null)
         {
            this.mbGamepadWaitingForCurrentPanel = true;
         }
         else
         {
            this.SetupAdapterWithCurrentPanel();
         }
         if(this.mInputAdapter.GetVisibleObjects().length)
         {
            return this.mInputAdapter.Enter(param1);
         }
         _loc7_ = this.GetFocusableBodyTypePanel();
         if(_loc7_)
         {
            return _loc7_.Enter(param1);
         }
         _loc3_ = this.mCurrentPanel.mcFilterPane;
         if(Boolean(_loc3_) && Boolean(_loc3_.visible))
         {
            return this.mFilterBubbleAdapter.Enter(param1);
         }
         return null;
      }
      
      protected function SetupAdapterWithCurrentPanel() : void
      {
         var _loc8_:int = 0;
         if(!this.mCurrentPanel || !this.mInputAdapter)
         {
            return;
         }
         var _loc1_:ScrollList = this.mCurrentPanel.mcTileList;
         if(!_loc1_)
         {
            return;
         }
         this.mbGamepadWaitingForCurrentPanel = false;
         this.mInputAdapter.SetGridLayout(_loc1_.mGridLayout as GridLayout);
         if(this.mResetInputAdapterHighlight)
         {
            this.mResetInputAdapterHighlight = false;
            _loc8_ = this.mCurrentPanel.GetFirstSelectedProductIndex();
            if(_loc8_ == -1)
            {
               _loc8_ = 0;
            }
            this.mInputAdapter.SetHighlightedIndex(_loc8_,true);
         }
         var _loc2_:ScrollListHelper = new ScrollListHelper(this.mInputAdapter);
         _loc2_.SetScrollList(_loc1_);
         _loc2_.SetOverrideMargin(CASCustomizerTunables.GAMEPAD_CUSTOMIZER_PANEL_MARGIN);
         this.mInputAdapter.SetSliderHelper(_loc2_);
         if(Boolean(this.mFilterBubbleAdapter) && Boolean(this.mCurrentPanel.mcFilterPane) && Boolean(this.mCurrentPanel.mcFilterPane.mcFilterBubble))
         {
            this.mFilterBubbleAdapter.SetElements(new <DisplayObject>[this.mCurrentPanel.mcFilterPane.mcFilterBubble.mcBackground]);
         }
         var _loc3_:ColorSwatchPanel = this.GetFocusableColorSwatch();
         if(_loc3_)
         {
            _loc3_.OnInputEventCall(InputAdapterEvent.LEAVE,this.HandleLeaveColorSwatch);
            _loc3_.OnInputEventCall(InputAdapterEvent.BACK,this.OnGamepadBack);
         }
         var _loc4_:HairGrowthPanel = this.GetFocusableHairGrowthPanel();
         if(_loc4_)
         {
            _loc4_.OnInputEventCall(InputAdapterEvent.LEAVE,this.HandleLeaveHairGrowth);
            _loc4_.OnInputEventCall(InputAdapterEvent.BACK,this.OnGamepadBack);
         }
         var _loc5_:ApplyAllPanel = this.GetFocusableApplyAllPanel();
         if(_loc5_)
         {
            _loc5_.OnInputEventCall(InputAdapterEvent.LEAVE,this.HandleLeaveApplyAll);
            _loc5_.OnInputEventCall(InputAdapterEvent.BACK,this.OnGamepadBack);
         }
         var _loc6_:CASLayerComponent = this.GetFocusableLayerComponent();
         if(_loc6_)
         {
            _loc6_.OnInputEventCall(InputAdapterEvent.LEAVE,this.HandleLeaveLayerComponent);
            _loc6_.OnInputEventCall(InputAdapterEvent.BACK,this.OnGamepadBack);
         }
         var _loc7_:CASBodyTypePanel = this.GetFocusableBodyTypePanel();
         if(_loc7_)
         {
            _loc7_.OnInputEventCall(InputAdapterEvent.LEAVE,this.HandleLeaveBodyType);
            _loc7_.OnInputEventCall(InputAdapterEvent.CONFIRM,this.HandleConfirmBodyType);
            _loc7_.OnInputEventCall(InputAdapterEvent.BACK,this.OnGamepadBack);
         }
         if(this.mCurrentPanel is ClothingPanel)
         {
            if((this.mCurrentPanel as ClothingPanel).HeaderIsPaintingPane())
            {
               this.mCurrentPanel.Header.OnInputEventCall(InputAdapterEvent.LEAVE,this.HandleLeaveHeader);
            }
         }
         if(this.mCurrentPanel is GenericCatalogPanel)
         {
            if(this.mCurrentPanel.Header)
            {
               this.mCurrentPanel.Header.OnInputEventCall(InputAdapterEvent.LEAVE,this.HandleLeaveHeader);
            }
            if(this.mCurrentPanel.Footer)
            {
               this.mCurrentPanel.Footer.OnInputEventCall(InputAdapterEvent.LEAVE,this.HandleLeaveFooter);
            }
         }
      }
      
      protected function HandleLeaveHeader(param1:InputAdapterLeaveEvent) : void
      {
         var _loc3_:CASFilterPane = null;
         var _loc4_:HairGrowthPanel = null;
         var _loc5_:ApplyAllPanel = null;
         var _loc2_:uint = uint(param1.GetDirection());
         if(_loc2_ == NavDirection.DOWN)
         {
            _loc3_ = this.mCurrentPanel.mcFilterPane;
            if(Boolean(_loc3_) && Boolean(_loc3_.visible))
            {
               NavManager.Instance.FocusPan(this.mFilterBubbleAdapter,param1.CreateEnterParams());
            }
            else
            {
               _loc4_ = this.GetFocusableHairGrowthPanel();
               if(_loc4_)
               {
                  NavManager.Instance.FocusPan(_loc4_,param1.CreateEnterParams());
                  return;
               }
               NavManager.Instance.FocusPan(this.mInputAdapter,param1.CreateEnterParams());
            }
         }
         if(_loc2_ == NavDirection.LEFT)
         {
            _loc5_ = this.GetFocusableApplyAllPanel();
            if(_loc5_)
            {
               NavManager.Instance.FocusPan(_loc5_,param1.CreateEnterParams());
            }
         }
      }
      
      protected function HandleLeaveFooter(param1:InputAdapterLeaveEvent) : void
      {
         var _loc2_:uint = uint(param1.GetDirection());
         if(_loc2_ == NavDirection.UP || _loc2_ == NavDirection.LEFT)
         {
            NavManager.Instance.FocusPan(this.mInputAdapter,param1.CreateEnterParams());
         }
      }
      
      protected function GetFocusableColorSwatch() : ColorSwatchPanel
      {
         var _loc1_:ColorSwatchPanel = null;
         if(this.mCurrentPanel is ColorSwatchCatalogPanel)
         {
            _loc1_ = (this.mCurrentPanel as ColorSwatchCatalogPanel).mcColorSwatchPanel;
            if(Boolean(_loc1_) && _loc1_.ShouldBeFocusable())
            {
               return _loc1_;
            }
         }
         return null;
      }
      
      protected function GetFocusableHairGrowthPanel() : HairGrowthPanel
      {
         var _loc1_:HairGrowthPanel = null;
         if(this.mCurrentPanel is ClothingPanel)
         {
            _loc1_ = (this.mCurrentPanel as ClothingPanel).mcHairGrowthPanel;
            if(Boolean(_loc1_) && Boolean(_loc1_.visible))
            {
               return _loc1_;
            }
         }
         return null;
      }
      
      protected function GetFocusableApplyAllPanel() : ApplyAllPanel
      {
         var _loc1_:ApplyAllPanel = null;
         if(this.mCurrentPanel is ClothingPanel)
         {
            _loc1_ = (this.mCurrentPanel as ClothingPanel).mcApplyToAllPanel;
            if(Boolean(_loc1_) && Boolean(_loc1_.visible))
            {
               return _loc1_;
            }
         }
         return null;
      }
      
      protected function GetFocusableLayerComponent() : CASLayerComponent
      {
         var _loc1_:CASLayerComponent = null;
         if(this.mCurrentPanel is ClothingPanel)
         {
            _loc1_ = (this.mCurrentPanel as ClothingPanel).mcLayerComponent;
            if(Boolean(_loc1_) && Boolean(_loc1_.visible))
            {
               return _loc1_;
            }
         }
         return null;
      }
      
      protected function GetFocusableBodyTypePanel() : CASBodyTypePanel
      {
         var _loc1_:CASBodyTypePanel = null;
         if(this.mCurrentPanel is ClothingPanel)
         {
            _loc1_ = (this.mCurrentPanel as ClothingPanel).mcBodyTypePanel;
            if(Boolean(_loc1_) && Boolean(_loc1_.visible))
            {
               return _loc1_;
            }
         }
         return null;
      }
      
      protected function HandlePostUndoRedo() : void
      {
         var _loc1_:int = 0;
         if(Boolean(this.mInputAdapter) && Boolean(this.mCurrentPanel))
         {
            _loc1_ = this.mCurrentPanel.GetFirstSelectedProductIndex();
            if(_loc1_ == -1)
            {
               if(this.mCurrentPanel.Footer is BreedsMixerPane)
               {
                  return;
               }
               _loc1_ = 0;
            }
            this.mInputAdapter.SetHighlightedIndex(_loc1_,false,this.mInputAdapter == NavManager.Instance.CurrentFocusable);
         }
      }
   }
}

