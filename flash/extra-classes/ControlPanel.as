package widgets.GameTray.controls
{
   import flash.display.MovieClip;
   import flash.events.Event;
   import flash.events.MouseEvent;
   import flash.geom.Point;
   import flash.geom.Rectangle;
   import flash.text.TextFieldAutoSize;
   import flash.utils.Dictionary;
   import flash.utils.getDefinitionByName;
   import flash.utils.getTimer;
   import gamedata.BuildBuy.Venues.VenueInfo;
   import gamedata.BuildBuy.constants.BuildBuyLocks;
   import gamedata.BuildBuy.constants.NavigationModes;
   import gamedata.BuildBuy.shared.BuildBuyStateData;
   import gamedata.BuildBuy.shared.ProductFilter;
   import gamedata.CAS.shared.CASConfiguration;
   import gamedata.CAS.shared.CASStateData;
   import gamedata.GameContent;
   import gamedata.Gameplay.Persistence.GameSaveLockUnlock;
   import gamedata.Gameplay.shared.GameplayStateData;
   import gamedata.MTX.MTXBundleData;
   import gamedata.TutorialTip.TutorialMode;
   import gamedata.shared.BuildBuyLockUnlock;
   import gamedata.shared.UiDialogNotification;
   import olympus.constants.DialogTypes;
   import olympus.constants.GameStateFlags;
   import olympus.constants.GameStates;
   import olympus.constants.WindowAnimation;
   import olympus.core.ConnectionManager;
   import olympus.core.ExtendableComponent;
   import olympus.core.OlympusObject;
   import olympus.core.Ticker;
   import olympus.core.UISettings;
   import olympus.core.widget.WidgetBase;
   import olympus.events.GenericEvent;
   import olympus.events.PushButtonEvent;
   import olympus.events.TickerEvent;
   import olympus.extensions.FlairExtension;
   import olympus.extensions.GoalExtension;
   import olympus.extensions.Selectability;
   import olympus.extensions.TelemetryExtension;
   import olympus.extensions.TooltipExtension;
   import olympus.extensions.TutorialTipExtension;
   import olympus.gamepad.LayoutAPI;
   import olympus.gamepad.NavManager;
   import olympus.gui.buttons.Button;
   import olympus.io.CommunicationManager;
   import olympus.io.TelemetryAttribute;
   import olympus.io.TelemetryManager;
   import olympus.localization.Keys;
   import olympus.localization.KeysBB;
   import olympus.localization.KeysCAS;
   import olympus.localization.KeysConsole;
   import olympus.localization.KeysEXCH;
   import olympus.localization.KeysGE;
   import olympus.localization.KeysGP;
   import olympus.localization.LocKey;
   import olympus.motion.TweenParams;
   import olympus.objects.SimPB;
   import olympus.objects.UMBaseData;
   import olympus.utils.Clamp;
   import olympus.utils.DisplayObjectUtils;
   import olympus.utils.FeatureParameterUtils;
   import olympus.utils.SystemUtils;
   import olympus.utils.WidgetUtils;
   import widgets.BuildBuy.data.CatalogData;
   import widgets.CAS.constants.CASSubStates;
   import widgets.CAS.controls.ScenarioRequirementsPanel;
   import widgets.GameTray.constants.GameTrayTunables;
   import widgets.Scenarios.constants.ScenarioTunables;
   import widgets.Tutorial.constants.TutorialTriggerEnums;
   import widgets.shared.GENeighborhoodStateManager;
   import widgets.shared.constants.ClientTutorialTrigger;
   import widgets.shared.constants.ExchangeSharedTunables;
   import widgets.shared.constants.GENeighborhoodMode;
   import widgets.shared.constants.GuidanceTipsSharedTunables;
   import widgets.shared.constants.StoreSharedTunables;
   import widgets.shared.constants.TelemetryConstants;
   import widgets.shared.constants.TransitionScreenMode;
   import widgets.shared.constants.TutorialTipUIElement;
   import widgets.shared.constants.WallViewMode;
   import widgets.shared.controls.Buttons.GenericCustomizableButton;
   import widgets.shared.data.Engagements.EngagementPageData;
   import widgets.shared.data.IncentiveAffordanceData;
   import widgets.shared.utils.DLCTrialsUtils;
   import widgets.shared.utils.IncentiveAffordanceUtils;
   import widgets.shared.utils.SharedExchangeUtils;
   import widgets.shared.utils.StoreUtils;
   import widgets.shared.utils.TelemetryUtils;
   
   [Embed(source="/_assets/assets.swf", symbol="symbol324")]
   public class ControlPanel extends ExtendableComponent
   {
      
      protected static const SHARE_PREFIX_MAP:Object = {
         "none":[""],
         "selected":["selected_",""],
         "full":["full_",""],
         "full_selected":["full_selected_",""],
         "mm":["mm_",""],
         "mm_selected":["mm_selected_",""]
      };
      
      protected static const WALL_PREFIX_MAP:Object = {
         "none":[""],
         "selected":["selected_",""],
         "mm":["mm_",""],
         "mm_selected":["mm_selected_",""]
      };
      
      protected static const PROMO_BUTTON_DISABLED:String = "0xca87f27ed9b4bb8e";
      
      protected static const FEATURE_PARAMETER_ON_STORE_CLICK_VARIATION_ID:String = "0x1f8ad4e537779a04";
      
      protected static const STORE_BUTTON_VARIATION_ALWAYS_STORE_ONE_EXCHANGE_PACK_DETAIL:int = 0;
      
      protected static const STORE_BUTTON_VARIATION_ALWAYS_STORE_ALWAYS_EXCHANGE_PACK_DETAIL:int = 1;
      
      protected static const STORE_BUTTON_VARIATION_NO_STORE_ALWAYS_EXCHANGE_PACK_DETAIL:int = 2;
      
      protected static const STORE_BUTTON_VARIATION_ALWAYS_STORE_NO_EXCHANGE_PACK_DETAIL:int = 3;
      
      public static const NOTIFICATION_STATE_PREFIX:String = "flair";
      
      public static const NOTIFICATION_PREFIX_MAP:Object = {
         "none":[""],
         "selected":["selected_",""],
         "flair":["flair_",""],
         "flair_selected":["flair_selected_","flair_","selected_",""]
      };
      
      public static const CONTROL_PANEL_GAME_STATE_SET:String = "controlPanelGameStateSet";
      
      protected static const WALL_TELEMETRY_NAME_ID:String = "WALL";
      
      protected static const SETUP_PROMO_DATA_VALID_GAME_STATES:Array = [GameStates.BUILD,GameStates.CAS,GameStates.LOT_SELECT,GameStates.PLAY,GameStates.TRAVEL];
      
      public var btnBuildBuy:Button;
      
      public var btnNeighborhood:Button;
      
      public var btnCamera:Button;
      
      public var btnEscapeMenu:Button;
      
      public var btnWall:Button;
      
      public var btnShare:Button;
      
      public var btnWallsUp:Button;
      
      public var btnWallsDown:Button;
      
      public var btnWallsCutaway:Button;
      
      public var btnSave:Button;
      
      public var btnManageHH:Button;
      
      public var mcFloorButtons:ExtendableComponent;
      
      public var mcHelpTab:MovieClip;
      
      public var btnFreeTrialTimer:FreeTrialTimerButton;
      
      public var btnLotFocus:Button;
      
      public var btnScenario:Button;
      
      public var btnGuidance:Button;
      
      public var mcStoreButtonContainer:MovieClip;
      
      protected var mbtnFloorUp:Button;
      
      protected var mbtnFloorDown:Button;
      
      protected var mBtnStore:StoreButton;
      
      protected var mGameState:uint;
      
      protected var mbIsWorldBuilder:Boolean;
      
      protected var mbIsLotPlayable:Boolean;
      
      protected var mbShowNbhdButton:Boolean;
      
      protected var mbIsLotEditable:Boolean;
      
      protected var mbIsSaveLoadLocked:Boolean = false;
      
      protected var mCurrentFloor:int;
      
      protected var mMinLevel:int;
      
      protected var mMaxLevel:int;
      
      protected var mWallState:int;
      
      protected var mWallButtons:Array = [];
      
      protected var mWallTelemtryLookUpTable:Array = [];
      
      protected var mbGeneticsPaneActive:Boolean = false;
      
      protected var mbCreateNewGame:Boolean = false;
      
      protected var mbIgnoreBuildBuyLockUnlock:Boolean = false;
      
      protected var mButtonToFrameMapping:Dictionary;
      
      protected var mcScenarioRequirementsPanel:ScenarioRequirementsPanel;
      
      protected var mNumFulfilledScenarioRequirements:int = 0;
      
      protected var mbGuidanceActive:Boolean = false;
      
      protected var mbStoreEnabled:Boolean = true;
      
      protected var mPromoPacks:Array = null;
      
      protected var mbShowStoreAnimation:Boolean = false;
      
      protected var mbShowStoreNotification:Boolean = false;
      
      protected var mTimeStoreToasterOpen:int = 0;
      
      protected var mBundlesToShow:Array = null;
      
      protected var mToastieData:IncentiveAffordanceData;
      
      protected var mToastieBundleInfo:MTXBundleData;
      
      protected var mToastieStoreFilterCTAInfo:Object;
      
      protected var mNotLinkedAffordances:Array;
      
      protected var mOnClickVariation:int = 0;
      
      protected var mFrameLabels:Object;
      
      protected var mbIsCFEBuild:Boolean;
      
      protected var mTelemetry:TelemetryExtension;
      
      public function ControlPanel()
      {
         addFrameScript(0,this.frame1,4,this.frame5,8,this.frame9,13,this.frame14,18,this.frame19,27,this.frame28,33,this.frame34,39,this.frame40,45,this.frame46,52,this.frame53,58,this.frame59,65,this.frame66,77,this.frame78,90,this.frame91,103,this.frame104,116,this.frame117,131,this.frame132,136,this.frame137,141,this.frame142,146,this.frame147,151,this.frame152,159,this.frame160,165,this.frame166,172,this.frame173,178,this.frame179,185,this.frame186,191,this.frame192,197,this.frame198,208,this.frame209,221,this.frame222,234,this.frame235,247,this.frame248,261,this.frame262,266,this.frame267,270,this.frame271,275,this.frame276,280,this.frame281,289,this.frame290,295,this.frame296,301,this.frame302,307,this.frame308,314,this.frame315,320,this.frame321,327,this.frame328,339,this.frame340,352,this.frame353,365,this.frame366,378,this.frame379,393,this.frame394,398,this.frame399,403,this.frame404,408,this.frame409,413,this.frame414,421,this.frame422,427,this.frame428,434,this.frame435,440,this.frame441
         ,447,this.frame448,453,this.frame454,459,this.frame460,470,this.frame471,483,this.frame484,496,this.frame497,509,this.frame510,523,this.frame524);
         super();
      }
      
      public function Initialize() : void
      {
         var _loc2_:TutorialTipExtension = null;
         var _loc1_:uint = CommunicationManager.CallGameService("GetGameState",null) as uint;
         this.mbIsWorldBuilder = CommunicationManager.CallGameService("IsWorldbuilder",null) as Boolean;
         this.mBtnStore = this.mcStoreButtonContainer.btnStore as StoreButton;
         this.mbtnFloorUp = this.mcFloorButtons.getChildByName("btnFloorUp") as Button;
         this.mbtnFloorDown = this.mcFloorButtons.getChildByName("btnFloorDown") as Button;
         _loc2_ = TutorialTipExtension.Get(this);
         _loc2_.ControlEnum = TutorialTipUIElement.BB_CAMERA;
         _loc2_.AddSatisfactionEvent(GenericEvent.CHANGE);
         _loc2_ = TutorialTipExtension.Get(this.mcFloorButtons);
         _loc2_.ControlEnum = TutorialTipUIElement.BB_CAMERA_FLOOR;
         _loc2_.AddSatisfactionEvent(GenericEvent.CHANGE);
         _loc2_ = TutorialTipExtension.Get(this.btnWallsUp);
         _loc2_.ControlEnum = TutorialTipUIElement.LIVE_WALL_BUTTON;
         _loc2_.AddSatisfactionEvent(GenericEvent.CHANGE);
         this.btnBuildBuy.mouseChildren = false;
         this.btnBuildBuy.addEventListener(PushButtonEvent.CLICK,this.OnBuildBuyClick,false,0,true);
         this.btnBuildBuy.TooltipExt.SetText(Keys.MODECONTROL_BUILD);
         this.btnBuildBuy.Selected = _loc1_ == GameStates.BUILD;
         this.btnBuildBuy.TooltipExt.UseHitAreaBounds = true;
         _loc2_ = TutorialTipExtension.Get(this.btnBuildBuy);
         _loc2_.ControlEnum = TutorialTipUIElement.LIVE_BUILD_BUTTON;
         _loc2_.AddSatisfactionEvent(PushButtonEvent.CLICK);
         _loc2_.ShouldHideImmediatelyOnSatisfy = true;
         _loc2_.AddSatisfactionMessage("GoToBuyMode");
         _loc2_.AddSatisfactionMessage("GoToBuildMode");
         var _loc3_:FlairExtension = FlairExtension.Get(this.btnBuildBuy);
         _loc3_.UiSettingSaveString = "ViewedFlairExtension_ControlPanelBB";
         _loc3_.EvaluateStatePrefix();
         this.btnNeighborhood.addEventListener(PushButtonEvent.CLICK,this.OnNeighborhoodClick,false,0,true);
         this.btnNeighborhood.TooltipExt.SetText(Keys.MODECONTROL_GOTO_NEIGHBORHOOD);
         TutorialTipExtension.Get(this.btnNeighborhood).ControlEnum = TutorialTipUIElement.LIVE_MANAGE_WORLDS_BUTTON;
         if(SystemUtils.UsingController)
         {
            this.btnNeighborhood.TooltipExt.SetToConstantlyUpdatePosition(false);
         }
         this.btnCamera.addEventListener(PushButtonEvent.CLICK,this.OnCameraClick,false,0,true);
         this.btnCamera.TooltipExt.SetText(SystemUtils.UsingController ? KeysConsole.FREE_CAM : KeysGP.CAMERA_CONTROLS);
         TutorialTipExtension.Get(this.btnCamera).ControlEnum = TutorialTipUIElement.CONTROL_PANEL_CAMERA;
         this.btnCamera.visible = _loc1_ != GameStates.CAS && _loc1_ != GameStates.LOT_SELECT && _loc1_ != GameStates.MAIN_MENU;
         this.btnLotFocus.addEventListener(PushButtonEvent.CLICK,this.OnLotFocusClick,false,0,true);
         this.btnLotFocus.TooltipExt.SetText(KeysGP.SIM_HUB_TOOLTIP_CENTER_ON_LOT);
         this.btnLotFocus.visible = _loc1_ == GameStates.PLAY;
         this.btnEscapeMenu.addEventListener(PushButtonEvent.CLICK,this.OnEscapeClick,false,0,true);
         this.btnEscapeMenu.TooltipExt.SetText(Keys.GAME_TRAY_TOOLTIP_ESCAPE);
         _loc2_ = TutorialTipExtension.Get(this.btnEscapeMenu);
         _loc2_.ControlEnum = TutorialTipUIElement.GLOBAL_ESCAPE_MENU_BUTTON;
         _loc2_.AddSatisfactionEvent(PushButtonEvent.CLICK);
         _loc2_.ShouldHideImmediatelyOnSatisfy = true;
         if(SystemUtils.UsingController)
         {
            _loc2_.AddSatisfactionMessage("ShowEscapeMenu");
            _loc2_.AddSatisfactionMessage("HideEscapeMenu");
         }
         this.btnManageHH.addEventListener(PushButtonEvent.CLICK,this.OnManageHouseholdClick,false,0,true);
         this.btnManageHH.TooltipExt.SetText(Keys.GAME_TRAY_TOOLTIP_HH_MANAGEMENT);
         this.btnManageHH.visible = _loc1_ == GameStates.LOT_SELECT || _loc1_ == GameStates.TRAVEL;
         _loc2_ = TutorialTipExtension.Get(this.btnManageHH);
         _loc2_.ControlEnum = TutorialTipUIElement.NHV_HOUSEHOLD_MANAGEMENT;
         _loc2_.AddSatisfactionEvent(PushButtonEvent.CLICK);
         _loc3_ = FlairExtension.Get(this.btnManageHH);
         _loc3_.UiSettingSaveString = "ViewedFlairExtension_ControlPanelManageHH";
         _loc3_.EvaluateStatePrefix();
         this.btnWall.addEventListener(PushButtonEvent.CLICK,this.OnWallClick,false,0,true);
         this.btnWall.PrefixMap = WALL_PREFIX_MAP;
         this.btnWall.TooltipExt.SetText(Keys.GAME_TRAY_TOOLTIP_NOTIFICATION_WALL);
         TutorialTipExtension.Get(this.btnWall).ControlEnum = TutorialTipUIElement.LIVE_NOTIFICATION_WALL_BUTTON;
         this.btnScenario.PrefixMap = NOTIFICATION_PREFIX_MAP;
         this.btnScenario.addEventListener(PushButtonEvent.CLICK,this.OnScenarioClick,false,0,true);
         this.btnScenario.TooltipExt.SetText(Keys.GAME_TRAY_TOOLTIP_SCENARIO);
         this.btnScenario.TooltipExt.UseHitAreaBounds = true;
         this.btnGuidance.addEventListener(PushButtonEvent.CLICK,this.OnGuidanceClick,false,0,true);
         this.btnGuidance.TooltipExt.SetText(Keys.GAME_TRAY_TOOLTIP_GUIDANCE);
         this.btnGuidance.TooltipExt.UseHitAreaBounds = true;
         TutorialTipExtension.Get(this.btnGuidance).ControlEnum = TutorialTipUIElement.CONTROL_PANEL_GUIDANCE;
         this.btnShare.addEventListener(PushButtonEvent.CLICK,SharedExchangeUtils.OnShareClick,false,-1,true);
         this.btnShare.AudioExt.ElementName = "ShareButton";
         this.btnShare.PrefixMap = SHARE_PREFIX_MAP;
         this.btnShare.TooltipExt.UseHitAreaBounds = true;
         _loc2_ = TutorialTipExtension.Get(this.btnShare);
         _loc2_.ControlEnum = TutorialTipUIElement.CAS_GALLERY_BUTTON;
         this.HandleOnlineAccessStateChanged(!ConnectionManager.IsOnlineAccessDisabled);
         this.mBtnStore.SetConfig(GameTrayTunables.GAME_TRAY_STORE_BUTTON_CONFIG);
         this.mBtnStore.addEventListener(PushButtonEvent.CLICK,this.OnStoreClick,false,0,true);
         this.mBtnStore.addEventListener(MouseEvent.ROLL_OVER,this.OnStoreMouseRollOver,false,0,true);
         this.mBtnStore.AudioExt.ElementName = "PurchaseButton";
         this.mBtnStore.TooltipExt.SetText(Keys.GAME_TRAY_TOOLTIP_STORE);
         this.mBtnStore.TooltipExt.UseHitAreaBounds = true;
         _loc2_ = TutorialTipExtension.Get(this.mBtnStore);
         _loc2_.ControlEnum = TutorialTipUIElement.CONTROL_PANEL_STORE_BUTTON;
         var _loc4_:GoalExtension = GoalExtension.Get(this.mBtnStore);
         _loc4_.ControlEnum = TutorialTipUIElement.CONTROL_PANEL_STORE_BUTTON;
         _loc4_.AddSatisfactionEvent(PushButtonEvent.CLICK);
         _loc4_.AddSatisfactionMessage("OpenDLCStore");
         this.btnSave.addEventListener(PushButtonEvent.CLICK,this.OnSaveClick,false,0,true);
         this.btnSave.TooltipExt.SetText(Keys.GAME_TRAY_TOOLTIP_HOUSEHOLD_SAVE);
         this.btnSave.AudioExt.ElementName = "HouseholdSaveButton";
         TutorialTipExtension.Get(this.btnSave).ControlEnum = TutorialTipUIElement.CAS_GALLERY_SAVE_BUTTON;
         if(SystemUtils.UsingController)
         {
            this.btnSave.visible = _loc1_ == GameStates.CAS;
         }
         this.mbtnFloorUp.addEventListener(PushButtonEvent.CLICK,this.OnFloorButtonClick,false,0,true);
         this.mbtnFloorUp.TooltipExt.SetText(Keys.GAME_TRAY_TOOLTIP_FLOOR_UP);
         this.mbtnFloorUp.AudioExt.ElementName = "FloorChangeButton";
         this.mbtnFloorDown.addEventListener(PushButtonEvent.CLICK,this.OnFloorButtonClick,false,0,true);
         this.mbtnFloorDown.TooltipExt.SetText(Keys.GAME_TRAY_TOOLTIP_FLOOR_DOWN);
         this.mbtnFloorDown.AudioExt.ElementName = "FloorChangeButton";
         this.btnWallsUp.hitArea = this.btnWallsUp["mcHitArea"];
         this.btnWallsUp.hitArea.visible = false;
         this.btnWallsUp.addEventListener(PushButtonEvent.CLICK,this.OnWallHeightClick,false,0,true);
         this.btnWallsUp.TooltipExt.SetText(KeysGP.CAMERA_WALLS_UP);
         this.btnWallsUp.AudioExt.ElementName = "WallsUpButton";
         this.mWallButtons.push(this.btnWallsUp);
         this.btnWallsDown.hitArea = this.btnWallsDown["mcHitArea"];
         this.btnWallsDown.hitArea.visible = false;
         this.btnWallsDown.addEventListener(PushButtonEvent.CLICK,this.OnWallHeightClick,false,0,true);
         this.btnWallsDown.TooltipExt.SetText(KeysGP.CAMERA_WALLS_DOWN);
         this.btnWallsDown.AudioExt.ElementName = "WallsDownButton";
         this.mWallButtons.push(this.btnWallsDown);
         this.btnWallsCutaway.hitArea = this.btnWallsCutaway["mcHitArea"];
         this.btnWallsCutaway.hitArea.visible = false;
         this.btnWallsCutaway.addEventListener(PushButtonEvent.CLICK,this.OnWallHeightClick,false,0,true);
         this.btnWallsCutaway.TooltipExt.SetText(KeysGP.CAMERA_WALLS_CUTAWAY);
         this.btnWallsCutaway.AudioExt.ElementName = "WallsCutawayButton";
         this.mWallButtons.push(this.btnWallsCutaway);
         this.mWallTelemtryLookUpTable.push("2");
         this.mWallTelemtryLookUpTable.push("0");
         this.mWallTelemtryLookUpTable.push("1");
         this.mbIsCFEBuild = CommunicationManager.CallGameService("IsConsumerFeedbackEnvironment");
         this.SetShareButtonEnabled();
         this.SetSaveButtonEnabled();
         CommunicationManager.AddMessageListener("SetGuidanceButtonEnabled",this.SetGuidanceButtonEnabled,this);
         CommunicationManager.AddMessageListener("ExitBuildMode",this.HandleExitBuildMode,this);
         CommunicationManager.AddMessageListener("GoToBuildMode",this.HandleGoToBuildMode,this);
         CommunicationManager.AddMessageListener("GoToBuyMode",this.HandleGoToBuyMode,this);
         CommunicationManager.AddMessageListener("GoToNeigborhoodTravel",this.HandleGoToNeigborhoodTravel,this);
         CommunicationManager.AddMessageListener("A11yTravelReady",this.A11yHandleTravelReady,this);
         CommunicationManager.AddMessageListener("A11yTravelResult",this.A11yHandleTravelResult,this);
         CommunicationManager.AddMessageListener("GoToShare",this.HandleGoToShare,this);
         CommunicationManager.AddMessageListener("RefreshModeControl",this.HandleRefreshModeControl,this);
         CommunicationManager.AddMessageListener("BBRefreshLevelData",this.RefreshFloorData,this);
         CommunicationManager.AddMessageListener("BBUpdateWallViewMode",this.RefreshWallData,this);
         CommunicationManager.AddMessageListener("ShowCameraControl",this.HandleShowCameraControl,this);
         CommunicationManager.AddMessageListener("ShowNotificationWall",this.HandleShowNotificationWall,this);
         CommunicationManager.AddMessageListener("ShowGuidanceTips",this.HandleShowGuidanceTips,this);
         CommunicationManager.AddMessageListener("OnlineAccessStateChanged",this.HandleOnlineAccessStateChanged,this);
         CommunicationManager.AddMessageListener("GENeighborhoodModeChanged",this.OnGENeighborhoodModeChanged,this);
         CommunicationManager.AddMessageListener("ScenarioRequirementsUpdate",this.OnScenarioRequirementsUpdate,this);
         CommunicationManager.AddMessageListener("ScenarioStarted",this.OnScenarioStarted,this);
         CommunicationManager.AddMessageListener("ScenarioEnded",this.OnScenarioEnded,this);
         CommunicationManager.AddMessageListener("OpenDLCStore",this.OpenDLCStore,this);
         CommunicationManager.AddMessageListener("FeatureParametersReceived",this.OnFeatureParametersReceived,this);
         CommunicationManager.AddMessageListener("ShowCASGeneticsPane",this.OnShowGeneticsPanel,this);
         CommunicationManager.AddMessageListener("HideCASGeneticsPane",this.OnHideGeneticsPanel,this);
         CommunicationManager.AddMessageListener("TransitionScreenUp",this.HandleTransitionScreenUp,this);
         CommunicationManager.AddMessageListener("UnloadedCameraControl",this.HandleUnloadedCameraControl,this);
         CommunicationManager.AddMessageListener("BuildBuyLockUnlock",this.HandleBuildBuyLockUnlock,this,BuildBuyLockUnlock);
         CommunicationManager.AddMessageListener("SituationsUpdated",this.HandleSituationChanged,this);
         CommunicationManager.AddMessageListener("SituationStart",this.HandleSituationChanged,this);
         CommunicationManager.AddMessageListener("SetControlPanelButtonsEnabled",this.HandleSetControlPanelButtonsEnabled,this);
         CommunicationManager.AddMessageListener("CASSubStateChanged",this.OnCASSubStateChanged,this);
         CommunicationManager.AddMessageListener("CASCatalogPanelFinishedAnimatingIn",this.OnCASCatalogPanelFinishedAnimatingIn,this);
         CommunicationManager.AddMessageListener("RequestControlPanelChangeFloor",this.HandleRequestControlPanelChangeFloor,this);
         CommunicationManager.AddMessageListener("RequestControlPanelSetFloor",this.HandleRequestControlPanelSetFloor,this);
         CommunicationManager.AddMessageListener("ShowControlHelpPane",this.HandleShowControlHelpPane,this);
         CommunicationManager.AddMessageListener("ControlPanelRefresh",this.HandleControlPanelRefresh,this);
         CommunicationManager.AddMessageListener("GuidanceItemActionActive",this.HandleGuidanceItemActionActive,this);
         CommunicationManager.AddMessageListener("GuidanceItemActionInactive",this.HandleGuidanceItemActionInactive,this);
         CommunicationManager.AddMessageListener("GuidanceHelpCenterClosed",this.HandleGuidanceHelpCenterClosed,this);
         CommunicationManager.AddMessageListener("GuidanceItemShown",this.HandleGuidanceItemShown,this);
         CommunicationManager.AddMessageListener("GuidanceItemHidden",this.HandleGuidanceItemHidden,this);
         CommunicationManager.RegisterServiceHandler("GetGuidanceButtonPosition",this.GetGuidanceButtonPosition,this);
         if(GameContent.HAS_EP05)
         {
            CommunicationManager.AddMessageListener("SeasonSelectShown",this.OnShowSeasonSelect,this);
            CommunicationManager.AddMessageListener("ReturnFromSeasonSelect",this.OnHideSeasonSelect,this);
         }
         var _loc5_:Array = this.currentLabels;
         var _loc6_:int = int(_loc5_.length);
         this.mFrameLabels = {};
         var _loc7_:int = 0;
         while(_loc7_ < _loc6_)
         {
            this.mFrameLabels[_loc5_[_loc7_].name] = true;
            _loc7_ = _loc7_ + 1;
         }
         this.SetupButtonToFrameMapping();
         if(SystemUtils.UsingConsoleInputMode)
         {
            this.SetupHelpTab();
            this.HandleShowControlHelpPane(CommunicationManager.CallGameService("OptionsGetValue",{"name":"ControlReminderEnabled"}) == true);
         }
         else
         {
            this.mcHelpTab.visible = false;
         }
         if(this.btnFreeTrialTimer)
         {
            this.btnFreeTrialTimer.Init();
         }
         this.SetUpDLCPromoButton();
         this.SetupOnClickVariation();
         this.SetGameState(_loc1_);
         this.mTelemetry = GetExtension(TelemetryExtension) as TelemetryExtension;
      }
      
      public function SetupButtonToFrameMapping() : void
      {
         this.mButtonToFrameMapping = new Dictionary(true);
         this.mButtonToFrameMapping[this.btnNeighborhood] = ["controller_build_from_nbhd","controller_build_from_nbhd_guidance","controller_live","controller_live_guidance","controller_build_from_nbhd_store","controller_build_from_nbhd_guidance_store","controller_live_store","controller_live_guidance_store"];
         this.mButtonToFrameMapping[this.btnCamera] = ["controller_build_from_nbhd","controller_build_from_nbhd_guidance","controller_build_from_live","controller_build_from_live_guidance","controller_live","controller_live_guidance","controller_build_from_nbhd_store","controller_build_from_nbhd_guidance_store","controller_build_from_live_store","controller_build_from_live_guidance_store","controller_live_store","controller_live_guidance_store"];
         this.mButtonToFrameMapping[this.btnEscapeMenu] = [];
         this.mButtonToFrameMapping[this.btnWall] = ["controller_build_from_nbhd","controller_build_from_nbhd_guidance","controller_build_from_live","controller_build_from_live_guidance","controller_world_builder","controller_live","controller_live_guidance","controller_travel","controller_travel_guidance","controller_nbhd","controller_nbhd_guidance","controller_cas","controller_cas_guidance","controller_cas_scenario","controller_cas_scenario_guidance","controller_build_from_nbhd_store","controller_build_from_nbhd_guidance_store","controller_build_from_live_store","controller_build_from_live_guidance_store","controller_world_builder_store","controller_live_store","controller_live_guidance_store","controller_travel_store","controller_travel_guidance_store","controller_nbhd_store","controller_nbhd_guidance_store","controller_cas_store","controller_cas_guidance_store","controller_cas_scenario_store","controller_cas_scenario_guidance_store"];
         this.mButtonToFrameMapping[this.btnShare] = ["controller_build_from_nbhd","controller_build_from_nbhd_guidance","controller_build_from_live","controller_build_from_live_guidance","controller_world_builder","controller_live","controller_live_guidance","controller_travel","controller_travel_guidance","controller_nbhd","controller_nbhd_guidance","controller_main_menu","controller_cas","controller_cas_guidance","controller_cas_scenario","controller_cas_scenario_guidance","controller_build_from_nbhd_store","controller_build_from_nbhd_guidance_store","controller_build_from_live_store","controller_build_from_live_guidance_store","controller_world_builder_store","controller_live_store","controller_live_guidance_store","controller_travel_store","controller_travel_guidance_store","controller_nbhd_store","controller_nbhd_guidance_store","controller_main_menu_store","controller_cas_store","controller_cas_guidance_store","controller_cas_scenario_store","controller_cas_scenario_guidance_store"];
         this.mButtonToFrameMapping[this.btnWallsUp] = [];
         this.mButtonToFrameMapping[this.btnWallsDown] = [];
         this.mButtonToFrameMapping[this.btnWallsCutaway] = [];
         this.mButtonToFrameMapping[this.mbtnFloorUp] = [];
         this.mButtonToFrameMapping[this.mbtnFloorDown] = [];
         this.mButtonToFrameMapping[this.btnSave] = ["controller_cas","controller_cas_guidance","controller_cas_scenario","controller_cas_scenario_guidance","controller_cas_store","controller_cas_guidance_store","controller_cas_scenario_store","controller_cas_scenario_guidance_store"];
         this.mButtonToFrameMapping[this.btnManageHH] = ["controller_travel","controller_travel_guidance","controller_nbhd","controller_nbhd_guidance","controller_travel_store","controller_travel_guidance_store","controller_nbhd_store","controller_nbhd_guidance_store"];
         this.mButtonToFrameMapping[this.btnBuildBuy] = ["controller_build_from_live","controller_build_from_live_guidance","controller_world_builder","controller_live","controller_live_guidance","controller_build_from_live_store","controller_build_from_live_guidance_store","controller_world_builder_store","controller_live_store","controller_live_guidance_store"];
         this.mButtonToFrameMapping[this.btnScenario] = ["controller_cas_scenario","controller_cas_scenario_guidance","controller_cas_scenario_store","controller_cas_scenario_guidance_store"];
         this.mButtonToFrameMapping[this.btnGuidance] = ["controller_build_from_nbhd_guidance","controller_build_from_live_guidance","controller_live_guidance","controller_travel_guidance","controller_nbhd_guidance","controller_cas_guidance","controller_cas_scenario_guidance","controller_cas_guidance_store","controller_cas_scenario_guidance_store","controller_nbhd_guidance_store","controller_travel_guidance_store","controller_live_guidance_store","controller_build_from_live_guidance_store","controller_build_from_nbhd_guidance_store"];
         this.mButtonToFrameMapping[this.mBtnStore] = ["controller_cas_store","ontroller_cas_scenario_store","controller_cas_guidance_store","controller_cas_scenario_guidance_store","controller_main_menu_store","controller_nbhd_store","controller_travel_store","controller_nbhd_guidance_store","controller_travel_guidance_store","controller_live_store","controller_live_guidance_store","controller_world_builder_store","controller_build_from_live_store","controller_build_from_live_guidance_store","controller_build_from_nbhd_store","controller_build_from_nbhd_guidance_store"];
      }
      
      public function HandleGameStateChange(param1:uint) : void
      {
         var _loc5_:GENeighborhoodStateManager = null;
         var _loc2_:Boolean = param1 == GameStates.MAIN_MENU;
         this.SetGameState(param1);
         if(SETUP_PROMO_DATA_VALID_GAME_STATES.indexOf(this.mGameState) != -1)
         {
            this.SetupDlcPromoData();
         }
         var _loc3_:Button = this.btnBuildBuy;
         if(param1 == GameStates.BUILD)
         {
            (_loc3_.GetExtension(FlairExtension) as FlairExtension).MarkAsSeen();
         }
         _loc3_.enabled = true;
         _loc3_.Selected = param1 == GameStates.BUILD;
         _loc3_.enabled = false;
         this.btnCamera.visible = param1 != GameStates.CAS && param1 != GameStates.LOT_SELECT && !_loc2_;
         this.btnLotFocus.visible = param1 == GameStates.PLAY;
         this.btnEscapeMenu.Selected = _loc2_;
         var _loc4_:Button = this.btnManageHH;
         _loc4_.visible = param1 == GameStates.LOT_SELECT || param1 == GameStates.TRAVEL;
         (_loc4_.GetExtension(TutorialTipExtension) as TutorialTipExtension).MarkVisibility(_loc4_.visible);
         if(this.btnGuidance)
         {
            TutorialTipExtension.Get(this.btnGuidance).MarkVisibility(this.btnGuidance.visible);
            this.SetGuidanceButtonEnabled();
            this.SelectGuidanceButton(false);
         }
         if(this.btnCamera)
         {
            TutorialTipExtension.Get(this.btnCamera).MarkVisibility(this.btnCamera.visible);
         }
         if(_loc4_.visible)
         {
            _loc5_ = GENeighborhoodStateManager.getInstance();
            this.UpdateHHManagementButton(_loc5_.Mode);
         }
         if(!this.btnCamera.visible)
         {
            this.btnCamera.Selected = false;
         }
         this.btnFreeTrialTimer.visible = DLCTrialsUtils.IsFreeTrial();
         this.mNumFulfilledScenarioRequirements = 0;
      }
      
      protected function OnGENeighborhoodModeChanged(param1:int) : void
      {
         this.UpdateHHManagementButton(param1);
         this.UpdateShareButtonEnabled(param1);
      }
      
      protected function UpdateHHManagementButton(param1:int) : void
      {
         var _loc2_:Button = this.btnManageHH;
         _loc2_.enabled = param1 == GENeighborhoodMode.EDIT;
         _loc2_.TooltipExt.SetText(_loc2_.enabled ? Keys.GAME_TRAY_TOOLTIP_HH_MANAGEMENT : GENeighborhoodMode.HUD_BUTTON_DISABLED_TOOLTIPS[param1]);
         (_loc2_.GetExtension(TutorialTipExtension) as TutorialTipExtension).MarkVisibility(_loc2_.enabled && _loc2_.visible);
      }
      
      protected function UpdateShareButtonEnabled(param1:int) : void
      {
         var _loc2_:Button = this.btnShare;
         _loc2_.enabled = param1 != GENeighborhoodMode.REINCARNATION;
         if(_loc2_.enabled)
         {
            this.UpdateShareButtonEnabledTooltip();
         }
         else
         {
            _loc2_.TooltipExt.SetText(GENeighborhoodMode.HUD_BUTTON_DISABLED_TOOLTIPS[param1]);
         }
         (_loc2_.GetExtension(TutorialTipExtension) as TutorialTipExtension).MarkVisibility(_loc2_.enabled && _loc2_.visible);
      }
      
      public function HandleGameStateLoadComplete(param1:uint) : void
      {
         this.QueryLotState();
         this.HandleGameSaveLockUnlock(GameplayStateData.SaveLockUnlockMessage);
         var _loc2_:Boolean = param1 == GameStates.BUILD || param1 == GameStates.PLAY || param1 == GameStates.LIVEEDIT;
         this.mbtnFloorDown.visible = _loc2_;
         this.mbtnFloorUp.visible = _loc2_;
         this.btnCamera.visible = _loc2_;
         if(!_loc2_)
         {
            this.btnWallsCutaway.visible = false;
            this.btnWallsDown.visible = false;
            this.btnWallsUp.visible = false;
         }
         else
         {
            this.RefreshFloorData();
            this.RefreshWallData();
         }
         this.SetGameState(param1);
         if(visible && currentFrameLabel.search("cas_scenario") != -1 && !CommunicationManager.CallUIService("IsGuidanceItemShown"))
         {
            this.SelectScenarioButton(true);
         }
      }
      
      protected function OnFeatureParametersReceived() : void
      {
         this.SetUpDLCPromoButton();
         this.SetupOnClickVariation();
      }
      
      protected function SetupOnClickVariation() : void
      {
         this.mOnClickVariation = FeatureParameterUtils.GetValueAsInt(FEATURE_PARAMETER_ON_STORE_CLICK_VARIATION_ID);
      }
      
      protected function SetUpDLCPromoButton() : void
      {
         this.mbStoreEnabled = !ConnectionManager.IsChildAccount && !FeatureParameterUtils.GetValueAsBoolean(PROMO_BUTTON_DISABLED);
         if(this.mbStoreEnabled)
         {
            this.GetDlcPromoData();
            this.mBtnStore.ShowAlert(false);
            CommunicationManager.AddMessageListener("TransitionScreenHidden",this.OnTransitionScreenHidden,this);
         }
      }
      
      protected function OnTransitionScreenHidden(param1:Object) : void
      {
         this.ShowStoreButtonNotificationIfNeeded();
      }
      
      public function HandleGameSaveLockUnlock(param1:GameSaveLockUnlock) : void
      {
         if(Boolean(param1) && param1.is_locked)
         {
            this.mbIsSaveLoadLocked = true;
            if(param1.mbLockGallery)
            {
               this.btnShare.enabled = false;
               this.btnShare.TooltipExt.SetText(param1.lock_reason);
            }
            if(this.mGameState == GameStates.PLAY)
            {
               this.btnBuildBuy.enabled = false;
               this.btnBuildBuy.TooltipExt.SetText(param1.lock_reason);
            }
            else
            {
               this.UpdateBuildBuyButtonState();
            }
         }
         else
         {
            this.mbIsSaveLoadLocked = false;
            this.SetShareButtonEnabled();
            this.UpdateBuildBuyButtonState();
         }
         this.UpdateNeighborhoodButtonState();
         this.UpdateStoreButtonState();
      }
      
      protected function HandleRefreshModeControl(param1:Object) : void
      {
         BuildBuyStateData.ClearStaticData();
         this.HandleGameStateLoadComplete(this.mGameState);
      }
      
      protected function HandleExitBuildMode(param1:Object) : void
      {
         if(this.mbIsLotPlayable)
         {
            this.ChangeGameStateToLive();
         }
         else
         {
            this.OnNeighborhoodClick(null);
         }
      }
      
      protected function HandleGoToBuildMode(param1:Object) : void
      {
         if(!this.btnBuildBuy.enabled || !this.mbIgnoreBuildBuyLockUnlock && new BuildBuyLockUnlock(CommunicationManager.CallGameService("GetBBLockUnlock")).build_buy_locked)
         {
            return;
         }
         var _loc2_:VenueInfo = BuildBuyStateData.CurrentVenueInfo;
         if(Boolean(!BuildBuyStateData.IsLotOwnedByPlayer) && Boolean(_loc2_) && _loc2_.IsRetailLot)
         {
            return;
         }
         if(this.mbIsLotEditable)
         {
            this.ChangeGameStateToBuild(NavigationModes.MAGALOG);
         }
      }
      
      protected function HandleGoToBuyMode(param1:Object) : void
      {
         if(!this.btnBuildBuy.enabled || !this.mbIgnoreBuildBuyLockUnlock && new BuildBuyLockUnlock(CommunicationManager.CallGameService("GetBBLockUnlock")).build_buy_locked)
         {
            return;
         }
         var _loc2_:VenueInfo = BuildBuyStateData.CurrentVenueInfo;
         if(Boolean(!BuildBuyStateData.IsLotOwnedByPlayer) && Boolean(_loc2_) && _loc2_.IsRetailLot)
         {
            return;
         }
         if(this.mbIsLotEditable)
         {
            this.ChangeGameStateToBuild(NavigationModes.BUY);
         }
      }
      
      protected function HandleGoToNeigborhoodTravel(param1:Object) : void
      {
         var _loc3_:SimPB = null;
         var _loc4_:UiDialogNotification = null;
         var _loc5_:Boolean = false;
         var _loc2_:Array = GameplayStateData.SelectableSims;
         for each(_loc3_ in _loc2_)
         {
            if(_loc3_.id == GameplayStateData.ActiveSimId)
            {
               if(!_loc3_.InZone)
               {
                  return;
               }
               break;
            }
         }
         if(GameplayStateData.IsBlockingSituationRunning)
         {
            _loc5_ = GameplayStateData.IsCareerSituationRunning;
            _loc4_ = new UiDialogNotification({
               "information_level":UiDialogNotification.LEVEL_SIM,
               "criticality":UiDialogNotification.CRITICALITY_URGENT,
               "text":(_loc5_ ? KeysGP.TRAVEL_BTN_DISABLED_BY_CAREER : KeysGP.TRAVEL_BTN_DISABLED_BY_EVENT)
            });
            CommunicationManager.CallGameService("CreateUiDialogNotification",_loc4_);
         }
         else if(GameplayStateData.SaveLocked)
         {
            _loc4_ = new UiDialogNotification({
               "information_level":UiDialogNotification.LEVEL_PLAYER,
               "text":GameplayStateData.SaveLockUnlockMessage.lock_reason
            });
            CommunicationManager.CallGameService("CreateUiDialogNotification",_loc4_);
         }
         else if(!this.A11yRouteTravel())
         {
            this.ChangeGameStateToNeighborhood(TransitionScreenMode.LIVE_TO_NHD_MAP_TRAVEL);
         }
      }

      // Screen Reader keyboard travel: with keyboard navigation and the
      // travel list on, Python answers the same M press with its companion
      // picker and destination list instead of the map. Routing needs a
      // fresh readiness lease from Python (TooltipManager.A11yTravelCanRoute);
      // without it the native map opens unchanged. One request is pending
      // at a time, bound to Python's session epoch; a pending request is
      // only released by Python's explicit result for that epoch and id, by
      // its cancel acknowledgement, or by a new epoch. It never times out
      // into the native map.
      protected var mA11yTravelEpoch:int = 0;
      protected var mA11yTravelRequest:int = 0;
      protected var mA11yTravelPending:int = 0;
      protected var mA11yTravelPendingEpoch:int = 0;
      protected var mA11yTravelSent:int = 0;
      protected var mA11yTravelCancelSent:Boolean = false;

      protected function A11yRouteTravel() : Boolean
      {
         var manager:Object = null;
         var now:int = 0;
         var attempted:Boolean = false;
         try
         {
            now = getTimer();
            if(this.mA11yTravelPending != 0)
            {
               // Python owns this press until it answers: never fall through
               // to the native map while a request is outstanding. After the
               // wait, ask Python to cancel once and keep waiting for its ack.
               if(!this.mA11yTravelCancelSent && now - this.mA11yTravelSent > 3000)
               {
                  this.A11yCancelTravel();
               }
               return true;
            }
            if(this.mGameState == GameStates.LOT_SELECT || this.mbIsSaveLoadLocked || GameStateFlags.IsBetweenStates || !GameplayStateData.HasSims)
            {
               return false;
            }
            manager = getDefinitionByName("olympus.core.TooltipManager");
            if(!manager["A11yTravelCanRoute"]())
            {
               return false;
            }
            this.mA11yTravelEpoch = int(manager["sA11yTravelLease"]);
            if(this.mA11yTravelEpoch <= 0)
            {
               return false;
            }
            this.mA11yTravelRequest = this.mA11yTravelRequest + 1;
            this.mA11yTravelPending = this.mA11yTravelRequest;
            this.mA11yTravelPendingEpoch = this.mA11yTravelEpoch;
            this.mA11yTravelSent = now;
            this.mA11yTravelCancelSent = false;
            attempted = true;
            CommunicationManager.CallGameService("PostServerCommand",{
               "command":"a11y.travel",
               "commandArgs":[this.mA11yTravelPendingEpoch,this.mA11yTravelPending]
            });
            return true;
         }
         catch(e:Error)
         {
         }
         // A failure after the dispatch attempt leaves Python possibly acting
         // on the request, so the press stays routed; before it, nothing was
         // sent and the native map is correct.
         return attempted;
      }

      protected function A11yCancelTravel() : void
      {
         this.mA11yTravelCancelSent = true;
         try
         {
            CommunicationManager.CallGameService("PostServerCommand",{
               "command":"a11y.travel_cancel",
               "commandArgs":[this.mA11yTravelPending,this.mA11yTravelPendingEpoch]
            });
         }
         catch(e:Error)
         {
         }
      }

      protected function A11yClearTravelPending() : void
      {
         this.mA11yTravelPending = 0;
         this.mA11yTravelPendingEpoch = 0;
         this.mA11yTravelCancelSent = false;
      }

      protected function A11yHandleTravelReady(param1:Object) : void
      {
         var epoch:int = 0;
         try
         {
            epoch = int(param1["epoch"]);
            // A new session epoch (zone load, pump restart) or no lease at all
            // means Python has dropped everything it had queued.
            if(this.mA11yTravelPending != 0 && epoch != this.mA11yTravelPendingEpoch)
            {
               this.A11yClearTravelPending();
            }
         }
         catch(e:Error)
         {
         }
      }

      protected function A11yHandleTravelResult(param1:Object) : void
      {
         try
         {
            if(this.mA11yTravelPending != 0 && int(param1["epoch"]) == this.mA11yTravelPendingEpoch && int(param1["request"]) == this.mA11yTravelPending)
            {
               this.A11yClearTravelPending();
            }
         }
         catch(e:Error)
         {
         }
      }
      
      protected function HandleGoToShare(param1:Object) : void
      {
         var _loc2_:Boolean = Boolean(param1) && Boolean(param1.bForceShowShare);
         if(!this.btnShare.enabled || Boolean(!_loc2_) && Boolean(CommunicationManager.CallUIService("IsDialogModalVisible")))
         {
            return;
         }
         if(CommunicationManager.CallUIService("IsWidgetVisible","ExchangeShare"))
         {
            WidgetUtils.HideExchangeWidgets();
         }
         else if(_loc2_ || !CommunicationManager.CallUIService("IsModalVisible"))
         {
            param1 ||= new Object();
            param1.bForceShowShare = true;
            if(!SharedExchangeUtils.DisplayShareLegalNotice(this.HandleGoToShare,param1))
            {
               CommunicationManager.SendUIMessage("ShowExchangeShare",{"mode":UISettings.SessionSettings.GetValue("lastViewedMode","share")});
            }
         }
      }
      
      protected function HandleTransitionScreenUp(param1:Object) : void
      {
         this.btnWall.Selected = false;
         CommunicationManager.SendUIMessage("HideNotificationWall",null);
         this.SelectScenarioButton(false);
         if(param1.mode == TransitionScreenMode.MAIN_MENU_TO_CAS)
         {
            if(this.mbCreateNewGame)
            {
               this.mbCreateNewGame = false;
               CommunicationManager.CallGameService("MainMenu_CreateNewGame");
            }
         }
      }
      
      public function HandleUnloadedCameraControl(param1:Object) : void
      {
         var _loc2_:Selectability = this.btnCamera.GetExtension(Selectability) as Selectability;
         _loc2_.Selected = false;
      }
      
      public function HandleBuildBuyLockUnlock(param1:BuildBuyLockUnlock) : void
      {
         this.UpdateBuildBuyButtonState();
      }
      
      protected function HandleSetControlPanelButtonsEnabled(param1:Object) : void
      {
         var _loc5_:Button = null;
         var _loc2_:Boolean = Boolean(param1.bEnabled);
         var _loc3_:int = 0;
         var _loc4_:int = numChildren;
         while(_loc3_ < _loc4_)
         {
            _loc5_ = getChildAt(_loc3_) as Button;
            if(_loc5_)
            {
               _loc5_.enabled = _loc2_;
            }
            _loc3_ = _loc3_ + 1;
         }
      }
      
      protected function HandleRequestControlPanelChangeFloor(param1:Object) : void
      {
         if(param1.floorChange)
         {
            this.ChangeFloor(param1.floorChange);
         }
      }
      
      protected function HandleRequestControlPanelSetFloor(param1:Object) : void
      {
         if(param1.floor != null)
         {
            this.SetFloor(param1.floor);
         }
      }
      
      protected function OnBuildBuyClick(param1:PushButtonEvent) : void
      {
         var _loc2_:Object = null;
         if(!this.btnBuildBuy.Selected)
         {
            this.btnBuildBuy.Selected = true;
            _loc2_ = UISettings.SessionSettings.GetValue("navMode");
            if(_loc2_ == null)
            {
               _loc2_ = NavigationModes.BUY;
            }
            if(this.ChangeGameStateToBuild(_loc2_ as int))
            {
               CommunicationManager.CallGameService("PostServerCommand",{
                  "command":"zone.trigger_test_event",
                  "commandArgs":[TutorialTriggerEnums.UIBuildButton]
               });
            }
            else
            {
               this.btnBuildBuy.Selected = false;
            }
         }
         else
         {
            this.ChangeGameStateToLive();
         }
      }
      
      protected function OnNeighborhoodClick(param1:PushButtonEvent) : void
      {
         if(this.mGameState == GameStates.PLAY)
         {
            CommunicationManager.SendUIMessage("ShowExitToManageWorldsDialog",{"context":TelemetryConstants.GE_MANAGE_WORLD_GAME_TRAY});
         }
         else if(!this.IsLotFulfilled())
         {
            this.ShowLotUnfulfilledDialog();
         }
         else if(!this.IsVenueFulfilled())
         {
            this.ShowVenueConfirmationDialog(this.OnNeighborhoodClickConfirm);
         }
         else
         {
            this.OnNeighborhoodClickConfirm();
         }
      }
      
      protected function OnNeighborhoodClickConfirm() : void
      {
         this.ChangeGameStateToNeighborhood(TransitionScreenMode.BUILD_TO_NHD_MAP);
      }
      
      protected function OnCameraClick(param1:PushButtonEvent) : void
      {
         var _loc2_:Selectability = null;
         if(SystemUtils.UsingController)
         {
            CommunicationManager.CallGameService("ToggleFreeCam");
            CommunicationManager.SendUIMessage("HideEscapeMenu");
         }
         else
         {
            _loc2_ = this.btnCamera.GetExtension(Selectability) as Selectability;
            _loc2_.Selected = !_loc2_.Selected;
            CommunicationManager.SendUIMessage((_loc2_.Selected ? "Show" : "Hide") + "CameraControl",null);
            CommunicationManager.CallGameService("PostServerCommand",{
               "command":"zone.trigger_test_event",
               "commandArgs":[TutorialTriggerEnums.UICameraButton]
            });
         }
      }
      
      protected function CloseCameraControl() : void
      {
         var _loc1_:Selectability = this.btnCamera.GetExtension(Selectability) as Selectability;
         if(Boolean(_loc1_) && _loc1_.Selected)
         {
            _loc1_.Selected = false;
            CommunicationManager.SendUIMessage("HideCameraControl");
         }
      }
      
      protected function OnLotFocusClick(param1:PushButtonEvent) : void
      {
         CommunicationManager.CallGameService("CameraCenterOnLot");
      }
      
      protected function OnEscapeClick(param1:PushButtonEvent) : void
      {
         CommunicationManager.SendUIMessage("ShowEscapeMenu",null);
      }
      
      protected function OnWallClick(param1:PushButtonEvent) : void
      {
         this.SelectScenarioButton(false);
         var _loc2_:Selectability = this.btnWall.GetExtension(Selectability) as Selectability;
         this.SelectNotificationWallButton(!_loc2_.Selected || SystemUtils.UsingController);
      }
      
      public function SelectNotificationWallButton(param1:Boolean) : void
      {
         var _loc4_:String = null;
         var _loc2_:Selectability = this.btnWall.GetExtension(Selectability) as Selectability;
         var _loc3_:Boolean = SystemUtils.UsingController;
         if(!_loc3_ || _loc2_.Selected != param1)
         {
            _loc2_.Selected = param1;
            _loc4_ = _loc2_.Selected ? "Show" : "Hide";
            CommunicationManager.SendUIMessage(_loc4_ + "NotificationWall",null);
         }
         if(_loc3_ && _loc2_.Selected)
         {
            NavManager.Instance.FocusWidgetForward("NotificationWall");
         }
      }
      
      protected function OnScenarioClick(param1:PushButtonEvent) : void
      {
         this.SelectNotificationWallButton(false);
         this.SelectGuidanceButton(false);
         var _loc2_:Selectability = this.btnScenario.GetExtension(Selectability) as Selectability;
         this.SelectScenarioButton(!_loc2_.Selected || SystemUtils.UsingController);
      }
      
      public function SelectScenarioButton(param1:Boolean) : void
      {
         var _loc2_:Selectability = this.btnScenario.GetExtension(Selectability) as Selectability;
         var _loc3_:Boolean = SystemUtils.UsingController;
         if(!_loc3_ || _loc2_.Selected != param1)
         {
            _loc2_.Selected = param1;
            this.OpenCloseScenarioPanel(_loc2_.Selected);
         }
         if(_loc3_ && _loc2_.Selected)
         {
            NavManager.Instance.FocusForward(this.mcScenarioRequirementsPanel);
         }
      }
      
      protected function SetScenarioButtonEnabled() : void
      {
         var _loc2_:LocKey = null;
         var _loc1_:uint = CASStateData.GetCASSubState();
         if(_loc1_ == CASSubStates.PETPAINTING)
         {
            this.btnScenario.enabled = false;
            this.btnScenario.TooltipExt.SetText(KeysCAS.PAINTING_PANEL_DISABLED_TOOLTIP);
            return;
         }
         if(_loc1_ == CASSubStates.STORIES || CASSubStates.AnyExpeditedSimState(_loc1_))
         {
            this.btnScenario.enabled = false;
            _loc2_ = CASSubStates.AnyExpeditedSimState(_loc1_) ? KeysCAS.CAS_STORIES_EXPEDITED_SIM_MODE_DISABLED_TOOLTIP : KeysCAS.CAS_STORIES_DISABLED_TOOLTIP;
            this.btnScenario.TooltipExt.SetText(_loc2_);
            return;
         }
         if(TutorialMode.IsFTUE() || this.mbGuidanceActive)
         {
            this.btnScenario.enabled = false;
            this.btnScenario.TooltipExt.SetText(Keys.GAME_TRAY_TOOLTIP_FTUE_HOUSEHOLD_SAVE_DISABLED);
            return;
         }
         if(this.btnGuidance.enabled && Boolean(CommunicationManager.CallUIService("IsGuidanceItemShown")))
         {
            this.btnScenario.enabled = false;
            this.btnScenario.TooltipExt.SetText(Keys.GAME_TRAY_TOOLTIP_GALLERY_TUTORIAL_DISABLED);
            return;
         }
         this.btnScenario.enabled = true;
         this.btnScenario.TooltipExt.SetText(Keys.GAME_TRAY_TOOLTIP_SCENARIO);
      }
      
      protected function SetupDlcPromoData() : void
      {
         var bToastieIsSet:Boolean;
         var bundleObjects:Array;
         var data:Object = null;
         var incentiveAffordances:Array = null;
         var packData:Object = null;
         var bBundleAlreadyAdded:Boolean = false;
         var bundleGameStates:Object = null;
         var bundleData:MTXBundleData = null;
         var retObj:Object = null;
         var packRecommendedText:String = null;
         this.mBundlesToShow = [];
         this.mToastieData = null;
         this.mToastieBundleInfo = null;
         this.mToastieStoreFilterCTAInfo = null;
         bToastieIsSet = false;
         bundleObjects = this.GetBundleDataObjectsForGameState(this.mPromoPacks);
         for each(data in this.mPromoPacks)
         {
            if(data)
            {
               if(data.hasOwnProperty("buttonCta"))
               {
                  if(!bToastieIsSet)
                  {
                     incentiveAffordances = this.SetupAffordancesFromPackData(data);
                     if(incentiveAffordances)
                     {
                        bToastieIsSet = this.SetToastieData(this.mBtnStore,incentiveAffordances);
                        if(bToastieIsSet)
                        {
                           this.mToastieStoreFilterCTAInfo = data;
                        }
                     }
                  }
               }
               else
               {
                  bBundleAlreadyAdded = bundleObjects.some(function(param1:Object):Boolean
                  {
                     return data.bundleId == param1.bundleId;
                  });
                  if(!bBundleAlreadyAdded)
                  {
                     bundleGameStates = data["gameStates"];
                     if(!bundleGameStates || bundleGameStates.length <= 0)
                     {
                        bundleObjects.push(data);
                     }
                  }
               }
            }
         }
         UISettings.SessionSettings.SetValue("ExchangePackDetail.LastPromoPackIndex",0);
         if(!bundleObjects || bundleObjects.length == 0)
         {
            return;
         }
         for each(packData in bundleObjects)
         {
            bundleData = null;
            retObj = CommunicationManager.CallGameService("GetBundleData",{"bundleId":packData.bundleId});
            if(retObj)
            {
               bundleData = new MTXBundleData(retObj);
            }
            if(!(!bundleData || bundleData.IsOwnedFull || bundleData.isInstalled))
            {
               if(!this.mbShowStoreNotification && !UISettings.AccountSettings.ListContainsValue(GameTrayTunables.PROMO_STORE_SETTINGS_KEY,packData.bundleId))
               {
                  this.mbShowStoreNotification = true;
                  this.mbShowStoreAnimation = true;
               }
               packRecommendedText = packData.recommendedText;
               if(packRecommendedText == null && Boolean(packData.isRecommended))
               {
                  packRecommendedText = KeysEXCH.DETAIL_MTX_RECOMMENDED_PACK_DEFAULT_TEXT.toString();
               }
               bundleData.bannerText = packRecommendedText;
               bundleData.umData = new UMBaseData(packData);
               this.mBundlesToShow.push(bundleData);
               if(!bToastieIsSet)
               {
                  incentiveAffordances = this.SetupAffordancesFromPackData(packData);
                  if(incentiveAffordances)
                  {
                     bToastieIsSet = this.SetToastieData(this.mBtnStore,incentiveAffordances);
                     if(bToastieIsSet)
                     {
                        this.mToastieBundleInfo = bundleData;
                     }
                  }
               }
            }
         }
         if(Boolean(!bToastieIsSet && this.mBundlesToShow.length > 0) && Boolean(this.mNotLinkedAffordances) && this.mNotLinkedAffordances.length > 0)
         {
            if(!(this.mNotLinkedAffordances[0] as OlympusObject))
            {
               OlympusObject.ConstructArrayInPlace(this.mNotLinkedAffordances,IncentiveAffordanceData);
            }
            this.SetToastieData(this.mBtnStore,this.mNotLinkedAffordances);
         }
         UISettings.AccountSettings.SetValue(GameTrayTunables.PROMO_STORE_SETTINGS_KEY,null);
         for each(packData in bundleObjects)
         {
            if(packData)
            {
               if(packData.hasOwnProperty("bundleId"))
               {
                  UISettings.AccountSettings.ListStoreValue(GameTrayTunables.PROMO_STORE_SETTINGS_KEY,packData.bundleId);
               }
            }
         }
         if(this.mbShowStoreNotification)
         {
            TelemetryManager.DispatchTelemetryEvent("GAME","DLCA","NOTF");
         }
      }
      
      protected function SetupAffordancesFromPackData(param1:Object) : Array
      {
         var _loc2_:Array = null;
         if(param1.hasOwnProperty("incentiveAffordances") && Boolean(param1["incentiveAffordances"]))
         {
            _loc2_ = param1["incentiveAffordances"] as Array;
            if(_loc2_.length > 0)
            {
               if(!(_loc2_[0] as OlympusObject))
               {
                  OlympusObject.ConstructArrayInPlace(_loc2_,IncentiveAffordanceData);
               }
               return _loc2_;
            }
         }
         return null;
      }
      
      protected function OpenCloseScenarioPanel(param1:Boolean) : void
      {
         var _loc3_:Number = NaN;
         var _loc4_:Point = null;
         var _loc5_:Rectangle = null;
         var _loc6_:Number = NaN;
         var _loc7_:TweenParams = null;
         var _loc8_:int = 0;
         var _loc2_:ScenarioRequirementsPanel = this.mcScenarioRequirementsPanel;
         if(param1)
         {
            if(Boolean(_loc2_) && contains(_loc2_))
            {
               return;
            }
            if(this.mbGuidanceActive)
            {
               return;
            }
            this.SetScenarioButtonEnabled();
            _loc2_ = this.mcScenarioRequirementsPanel = new ScenarioRequirementsPanel();
            addChild(_loc2_);
            _loc2_.visible = true;
            _loc3_ = LayoutAPI.StageWidth - _loc2_.width;
            _loc4_ = this.globalToLocal(new Point(_loc3_,0));
            _loc2_.x = _loc4_.x;
            _loc5_ = this.btnScenario.hitArea.getBounds(this.btnScenario.stage);
            _loc2_.y = _loc5_.bottom + ScenarioTunables.SCENARIO_REQUIREMENTS_SPACING_FROM_CONTROL_PANEL;
            _loc6_ = this.btnScenario.x + this.btnScenario.hitArea.width / 2;
            _loc2_.mcArrow.x = _loc6_ - _loc2_.x - ScenarioTunables.SCENARIO_REQUIREMENTS_LIST_BACKGROUND_ARROW_OFFSET;
            _loc7_ = WindowAnimation.PANEL_LARGE_VERT_IN;
            _loc8_ = _loc2_.AnimateIn(0,_loc7_,ScenarioTunables.SCENARIO_REQUIREMENTS_ANIMATION_REG_POINT);
            DisplayObjectUtils.CreateInputBlocker(_loc2_,_loc8_);
            this.btnScenario.DisableStatePrefix(NOTIFICATION_STATE_PREFIX);
            if(SystemUtils.UsingConsoleInputMode)
            {
               CommunicationManager.RegisterServiceHandler("ScenariosPanelIsVisible",this.HandleScenariosPanelIsVisible,this);
            }
         }
         else if(Boolean(_loc2_) && contains(_loc2_))
         {
            _loc8_ = _loc2_.AnimateOut(0,WindowAnimation.PANEL_OUT,ScenarioTunables.SCENARIO_REQUIREMENTS_ANIMATION_REG_POINT);
            DisplayObjectUtils.CreateInputBlocker(_loc2_,_loc8_,null,this.OnScenarioPanelHidden);
         }
      }
      
      protected function OnScenarioPanelHidden() : void
      {
         if(this.mcScenarioRequirementsPanel)
         {
            if(SystemUtils.UsingConsoleInputMode)
            {
               CommunicationManager.UnregisterServiceHandler("ScenariosPanelIsVisible",this.HandleScenariosPanelIsVisible,this);
            }
            this.mcScenarioRequirementsPanel.visible = false;
            removeChild(this.mcScenarioRequirementsPanel);
            this.mcScenarioRequirementsPanel = null;
         }
      }
      
      protected function HandleScenariosPanelIsVisible() : Boolean
      {
         return true;
      }
      
      protected function OnScenarioRequirementsUpdate(param1:Object) : void
      {
         var _loc4_:Object = null;
         if(!param1)
         {
            return;
         }
         var _loc2_:Array = param1["requirements"] as Array;
         var _loc3_:int = this.mNumFulfilledScenarioRequirements;
         this.mNumFulfilledScenarioRequirements = 0;
         for each(_loc4_ in _loc2_)
         {
            if(_loc4_["state"] == true)
            {
               this.mNumFulfilledScenarioRequirements = this.mNumFulfilledScenarioRequirements + 1;
            }
         }
         if(Boolean(this.mcScenarioRequirementsPanel) && this.mcScenarioRequirementsPanel.visible)
         {
            this.mcScenarioRequirementsPanel.HandleScenarioRequirementsUpdate(param1);
         }
         else if(this.mNumFulfilledScenarioRequirements < _loc3_)
         {
            this.SelectScenarioButton(true);
         }
         else
         {
            this.btnScenario.EnableStatePrefix(NOTIFICATION_STATE_PREFIX);
         }
      }
      
      protected function OnScenarioStarted() : void
      {
         this.SetGameState(this.mGameState);
         this.SelectScenarioButton(true);
      }
      
      protected function OnScenarioEnded(param1:Object) : void
      {
         this.SelectScenarioButton(false);
         this.SetGameState(this.mGameState);
      }
      
      protected function GetGuidanceButtonPosition() : Point
      {
         var _loc1_:Rectangle = this.btnGuidance.hitArea.getBounds(this.btnGuidance.stage);
         return new Point(_loc1_.x,_loc1_.bottom);
      }
      
      protected function OnGuidanceClick(param1:PushButtonEvent) : void
      {
         var _loc2_:Selectability = this.btnGuidance.GetExtension(Selectability) as Selectability;
         this.SelectGuidanceButton(!_loc2_.Selected || SystemUtils.UsingController);
      }
      
      public function SelectGuidanceButton(param1:Boolean, param2:Boolean = false) : void
      {
         var _loc5_:Object = null;
         var _loc3_:Selectability = this.btnGuidance.GetExtension(Selectability) as Selectability;
         var _loc4_:Boolean = SystemUtils.UsingController;
         if(!_loc4_ || _loc3_.Selected != param1)
         {
            _loc3_.Selected = param1;
            if(!param2)
            {
               _loc5_ = _loc3_.Selected ? null : {"showType":GuidanceTipsSharedTunables.PANE_SHOW_NOTHING};
               CommunicationManager.SendUIMessage("ShowGuidanceTips",_loc5_);
            }
         }
      }
      
      protected function OnSaveClick(param1:PushButtonEvent) : void
      {
         if(this.mGameState == GameStates.CAS)
         {
            CommunicationManager.SendUIMessage("CASSaveGame",this.btnSave);
         }
      }
      
      protected function GetDlcPromoData() : void
      {
         if(!this.mBundlesToShow)
         {
            CommunicationManager.AddMessageListener("DlcPromoDataResponse",this.HandleDlcPromoDataResponse,this);
            CommunicationManager.CallGameService("GetPromoBundleData",{
               "response":"DlcPromoDataResponse",
               "destination":"TS4_DLCAwareness"
            });
         }
      }
      
      protected function HandleDlcPromoDataResponse(param1:Object) : void
      {
         if(!param1 || !param1.hasOwnProperty("bundles"))
         {
            return;
         }
         this.mPromoPacks = param1["bundles"] as Array;
         this.mNotLinkedAffordances = param1["incentiveAffordances"] as Array;
         if(!this.mPromoPacks || this.mPromoPacks.length == 0)
         {
            return;
         }
         if(SETUP_PROMO_DATA_VALID_GAME_STATES.indexOf(this.mGameState) != -1)
         {
            this.SetupDlcPromoData();
         }
      }
      
      public function SetToastieData(param1:GenericCustomizableButton, param2:Array) : Boolean
      {
         var i:int;
         var n:int;
         var item:IncentiveAffordanceData = null;
         var button:GenericCustomizableButton = param1;
         var incentiveAffordances:Array = param2;
         if(incentiveAffordances == null)
         {
            return false;
         }
         incentiveAffordances = incentiveAffordances.filter(function(param1:IncentiveAffordanceData):Boolean
         {
            return param1.IsValidForGameState(mGameState);
         });
         i = 0;
         n = int(incentiveAffordances.length);
         while(i < n)
         {
            item = incentiveAffordances[i];
            if(!(item == null || item.affordanceType != IncentiveAffordanceData.AFFORDANCE_TYPE_TOASTIE))
            {
               if(item.persistence == IncentiveAffordanceData.AFFORDANCE_PERSISTENCE_ONCE && IncentiveAffordanceUtils.HasSeenAffordance(item,"storeAccess"))
               {
                  this.mToastieData = null;
               }
               else if(button)
               {
                  this.mToastieData = item;
                  button.ToastieHideOnClick = item.persistence != IncentiveAffordanceData.AFFORDANCE_PERSISTENCE_PERMANENT;
                  return true;
               }
            }
            i = i + 1;
         }
         return false;
      }
      
      protected function ShowStoreButtonNotificationIfNeeded() : void
      {
         var _loc1_:* = undefined;
         if(SETUP_PROMO_DATA_VALID_GAME_STATES.indexOf(this.mGameState) == -1 || !this.mbStoreEnabled || !this.mBtnStore.enabled)
         {
            return;
         }
         if(CommunicationManager.CallUIService("IsUILoading"))
         {
            return;
         }
         if(this.mbShowStoreNotification)
         {
            this.mBtnStore.ShowAlert(true);
         }
         if(this.mToastieData)
         {
            if(!this.mBtnStore.IsToastieVisible)
            {
               _loc1_ = {
                  "gmod":TelemetryUtils.GetStoreTelemetryContextFromGameState(this.mGameState),
                  "mesg":this.mToastieData.messageId
               };
               TelemetryManager.DispatchTelemetryEvent(TelemetryManager.GAME,"TOST","VIEW",_loc1_);
            }
            this.mBtnStore.ToastieData = this.mToastieData;
            IncentiveAffordanceUtils.SetSeenAffordance(this.mToastieData,"storeAccess");
            if(this.mToastieData.id)
            {
               this.mToastieData.SendUMViewEvent();
            }
         }
      }
      
      protected function OnStoreClick(param1:PushButtonEvent) : void
      {
         this.OpenDLCStore();
      }
      
      protected function OnStoreMouseRollOver(param1:MouseEvent) : void
      {
         this.RemoveToaster();
      }
      
      protected function RemoveToaster() : void
      {
         this.mBtnStore.HideToastie();
         this.mTimeStoreToasterOpen = (getTimer() - this.mBtnStore.GetToastieOpenedTime()) / 1000;
      }
      
      protected function OpenDLCStore() : void
      {
         if(!this.mbStoreEnabled || !this.mBtnStore.enabled || !this.mBtnStore.visible)
         {
            return;
         }
         var _loc1_:Boolean = this.mBtnStore.IsNotificationDotVisible;
         this.mBtnStore.ShowAlert(false);
         var _loc2_:FlairExtension = FlairExtension.Get(this.mBtnStore,false);
         if(_loc2_)
         {
            _loc2_.EvaluateStatePrefix(false);
         }
         this.mbShowStoreNotification = false;
         this.mbShowStoreAnimation = false;
         var _loc3_:int = UISettings.SessionSettings.GetValue("ExchangePackDetail.LastPromoPackIndex") as int;
         var _loc4_:int = 0;
         switch(this.mGameState)
         {
            case GameStates.BUILD:
               _loc4_ = TelemetryConstants.EXCH_PACK_DETAIL_CONTEXT_PROMO_BUILD;
               break;
            case GameStates.CAS:
               _loc4_ = TelemetryConstants.EXCH_PACK_DETAIL_CONTEXT_PROMO_CAS;
               break;
            case GameStates.LOT_SELECT:
               _loc4_ = TelemetryConstants.EXCH_PACK_DETAIL_CONTEXT_PROMO_LOT_SELECT;
               break;
            case GameStates.PLAY:
               _loc4_ = TelemetryConstants.EXCH_PACK_DETAIL_CONTEXT_PROMO_LIVE;
               break;
            case GameStates.TRAVEL:
               _loc4_ = TelemetryConstants.EXCH_PACK_DETAIL_CONTEXT_PROMO_TRAVEL;
         }
         if(!this.ShowStoreWithLinkedToastie(_loc3_,_loc4_,_loc1_))
         {
            this.ShowStoreWithOnClickVariation(_loc3_,_loc4_,_loc1_);
         }
      }
      
      protected function ShowStoreWithOnClickVariation(param1:int, param2:int, param3:Boolean) : void
      {
         var _loc6_:Boolean = false;
         var _loc4_:Boolean = this.mOnClickVariation != STORE_BUTTON_VARIATION_NO_STORE_ALWAYS_EXCHANGE_PACK_DETAIL;
         var _loc5_:Boolean = false;
         switch(this.mOnClickVariation)
         {
            case STORE_BUTTON_VARIATION_ALWAYS_STORE_ONE_EXCHANGE_PACK_DETAIL:
               _loc6_ = !(UISettings.SessionSettings.GetValue("StoreButtonExchangePackDetailsSeen","packDetailSeen") as Boolean);
               StoreUtils.OpenStorePage(EngagementPageData.ENGAGEMENT_PAGE_TYPE_BROWSE,WidgetUtils.GetBaseName(this));
               if(Boolean(_loc6_) && Boolean(this.mBundlesToShow) && this.mBundlesToShow.length > 0)
               {
                  UISettings.SessionSettings.SetValue("StoreButtonExchangePackDetailsSeen",true,"packDetailSeen");
                  _loc5_ = true;
                  this.ShowExchangePackDetail(param1,param2,param3);
               }
               break;
            case STORE_BUTTON_VARIATION_ALWAYS_STORE_ALWAYS_EXCHANGE_PACK_DETAIL:
               StoreUtils.OpenStorePage(EngagementPageData.ENGAGEMENT_PAGE_TYPE_BROWSE,WidgetUtils.GetBaseName(this));
               if(Boolean(this.mBundlesToShow) && this.mBundlesToShow.length > 0)
               {
                  _loc5_ = true;
                  this.ShowExchangePackDetail(param1,param2,param3);
               }
               break;
            case STORE_BUTTON_VARIATION_NO_STORE_ALWAYS_EXCHANGE_PACK_DETAIL:
               if(!this.mBundlesToShow || this.mBundlesToShow.length == 0)
               {
                  this.ShowStoreNothingToShowDialog();
               }
               else
               {
                  _loc5_ = true;
                  this.ShowExchangePackDetail(param1,param2,param3);
               }
               break;
            case STORE_BUTTON_VARIATION_ALWAYS_STORE_NO_EXCHANGE_PACK_DETAIL:
               StoreUtils.OpenStorePage(EngagementPageData.ENGAGEMENT_PAGE_TYPE_BROWSE,WidgetUtils.GetBaseName(this));
         }
         this.SetupStoreAndPDPTelemetry(_loc4_,_loc5_,false);
      }
      
      protected function ShowStoreWithLinkedToastie(param1:int, param2:int, param3:Boolean) : Boolean
      {
         var _loc6_:Array = null;
         var _loc7_:MTXBundleData = null;
         var _loc8_:String = null;
         var _loc9_:Object = null;
         if(!this.mToastieData)
         {
            return false;
         }
         this.RemoveToaster();
         var _loc4_:Boolean = this.mOnClickVariation != STORE_BUTTON_VARIATION_NO_STORE_ALWAYS_EXCHANGE_PACK_DETAIL;
         var _loc5_:Boolean = false;
         if(this.mToastieBundleInfo)
         {
            _loc6_ = [];
            _loc6_.push(this.mToastieBundleInfo);
            for each(_loc7_ in this.mBundlesToShow)
            {
               if(_loc7_.bundleId != this.mToastieBundleInfo.bundleId)
               {
                  _loc6_.push(_loc7_);
               }
            }
            UISettings.SessionSettings.SetValue("StoreButtonExchangePackDetailsSeen",true,"packDetailSeen");
            if(_loc4_)
            {
               StoreUtils.OpenStorePage(EngagementPageData.ENGAGEMENT_PAGE_TYPE_BROWSE,WidgetUtils.GetBaseName(this));
            }
            _loc5_ = true;
            this.ShowExchangePackDetail(param1,param2,param3,_loc6_);
            this.mToastieBundleInfo = null;
         }
         else if(Boolean(this.mToastieStoreFilterCTAInfo) && Boolean(this.mToastieStoreFilterCTAInfo.buttonCta))
         {
            StoreUtils.OpenStorePage(EngagementPageData.ENGAGEMENT_PAGE_TYPE_BROWSE,WidgetUtils.GetBaseName(this));
            _loc8_ = this.mToastieStoreFilterCTAInfo.buttonCta;
            if(_loc8_ != "store")
            {
               _loc9_ = {};
               _loc9_["context"] = param2;
               CommunicationManager.CallGameService("ExecuteCallToActionURL",{
                  "cta":_loc8_,
                  "umBaseData":this.mToastieStoreFilterCTAInfo,
                  "telemetry":_loc9_
               });
            }
            this.mToastieStoreFilterCTAInfo = null;
         }
         else
         {
            if(_loc4_)
            {
               StoreUtils.OpenStorePage(EngagementPageData.ENGAGEMENT_PAGE_TYPE_BROWSE,WidgetUtils.GetBaseName(this));
            }
            if(Boolean(this.mBundlesToShow) && this.mBundlesToShow.length > 0)
            {
               UISettings.SessionSettings.SetValue("StoreButtonExchangePackDetailsSeen",true,"packDetailSeen");
               _loc5_ = true;
               this.ShowExchangePackDetail(param1,param2,param3);
            }
            else if(!_loc4_)
            {
               this.ShowStoreNothingToShowDialog();
            }
         }
         this.SetupStoreAndPDPTelemetry(_loc4_,_loc5_,true);
         this.mToastieData = null;
         return true;
      }
      
      protected function ShowExchangePackDetail(param1:int, param2:int, param3:Boolean, param4:Array = null) : void
      {
         var _loc5_:Array = param4 ? param4 : this.mBundlesToShow;
         if(!_loc5_ || _loc5_.length == 0)
         {
            return;
         }
         var _loc6_:MTXBundleData = _loc5_[param1] as MTXBundleData;
         if(!_loc6_)
         {
            return;
         }
         var _loc7_:Object = {
            "bundleId":_loc6_.bundleId,
            "context":param2,
            "dlcButtonNotification":param3,
            "timeToasterOpen":this.mTimeStoreToasterOpen
         };
         if(this.mToastieData)
         {
            _loc7_["toastieData"] = this.mToastieData;
         }
         SharedExchangeUtils.ShowExchangePackDetail(_loc7_,false);
      }
      
      protected function SetupStoreAndPDPTelemetry(param1:Boolean, param2:Boolean, param3:Boolean) : void
      {
         var _loc4_:int = FeatureParameterUtils.GetValueAsInt(FEATURE_PARAMETER_ON_STORE_CLICK_VARIATION_ID);
         var _loc5_:Object = {
            "gmod":TelemetryUtils.GetStoreTelemetryContextFromGameState(this.mGameState),
            "dlcn":param3,
            "rslt":_loc4_
         };
         if(param1)
         {
            if(!TelemetryManager.HasSessionValue(StoreSharedTunables.STORE_TELEMETRY_SESSION_NAME) || TelemetryManager.GetSessionValue(StoreSharedTunables.STORE_TELEMETRY_SESSION_NAME) == "")
            {
               TelemetryManager.SetSessionValue(StoreSharedTunables.STORE_TELEMETRY_SESSION_NAME,getTimer());
            }
            _loc5_["stvs"] = TelemetryManager.GetSessionValueAsInt(StoreSharedTunables.STORE_TELEMETRY_SESSION_NAME);
         }
         if(param2)
         {
            if(!param1)
            {
               TelemetryManager.SetSessionValue(StoreSharedTunables.STORE_TELEMETRY_SESSION_NAME,getTimer());
            }
            TelemetryManager.SetSessionValue(ExchangeSharedTunables.EXCHANGE_PACK_DETAIL_TELEMETRY_SESSION_NAME,getTimer());
            _loc5_["pdvs"] = TelemetryManager.GetSessionValueAsInt(ExchangeSharedTunables.EXCHANGE_PACK_DETAIL_TELEMETRY_SESSION_NAME);
         }
         if(this.mToastieData)
         {
            _loc5_["mesg"] = this.mToastieData.messageId;
            _loc5_["tost"] = this.mTimeStoreToasterOpen;
         }
         TelemetryManager.DispatchTelemetryEvent(TelemetryManager.GAME,"CART","CLCK",_loc5_);
      }
      
      protected function ShowStoreNothingToShowDialog() : void
      {
         CommunicationManager.SendUIMessage("ShowDialog",{
            "dialog_id":"Purchase-NothingToShow",
            "type":DialogTypes.YES,
            "title":Keys.GAME_TRAY_STORE_NOTHING_TO_SHOW_TITLE,
            "description":Keys.GAME_TRAY_STORE_NOTHING_TO_SHOW_DESCRIPTION,
            "optionOneText":Keys.GENERIC_OK
         });
      }
      
      protected function OnStoreFlairTimeout(param1:TickerEvent) : void
      {
         var _loc2_:FlairExtension = FlairExtension.Get(this.mBtnStore,false);
         if(_loc2_)
         {
            _loc2_.EvaluateStatePrefix(false);
         }
         Ticker.Remove(this.mBtnStore);
         this.mbShowStoreAnimation = false;
      }
      
      protected function OnFloorButtonClick(param1:PushButtonEvent) : void
      {
         var _loc2_:Button = null;
         _loc2_ = param1.target as Button;
         var _loc3_:uint = _loc2_ == this.mbtnFloorUp ? 1 : uint(-1);
         this.ChangeFloor(_loc3_);
      }
      
      protected function ChangeFloor(param1:int) : void
      {
         var _loc2_:int = Clamp.Int(this.mCurrentFloor + param1,this.mMinLevel,this.mMaxLevel);
         this.SetFloor(_loc2_);
      }
      
      protected function SetFloor(param1:int) : void
      {
         if(param1 != this.mCurrentFloor)
         {
            this.mCurrentFloor = param1;
            CommunicationManager.CallGameService("BBSetLevel",this.mCurrentFloor);
            dispatchEvent(new Event(GenericEvent.CHANGE));
            this.mcFloorButtons.dispatchEvent(new Event(GenericEvent.CHANGE));
         }
      }
      
      protected function OnManageHouseholdClick(param1:PushButtonEvent) : void
      {
         FlairExtension.Get(this.btnManageHH).MarkAsSeen();
         CommunicationManager.SendUIMessage("ShowGameEntryHouseholdPanel");
         this.TryShowStoryProgressionDialog();
         CommunicationManager.CallUIService("HideDockTray");
      }
      
      protected function TryShowStoryProgressionDialog() : void
      {
         var spDisabled:Boolean;
         var telemExt:TelemetryExtension = null;
         if(TutorialMode.IsFTUE())
         {
            return;
         }
         spDisabled = CommunicationManager.CallGameService("GetStoryProgressionDisabled") as Boolean;
         if(spDisabled)
         {
            return;
         }
         if(UISettings.AccountSettings.GetValue("ge.storyProgressionSeen") as Boolean)
         {
            return;
         }
         UISettings.AccountSettings.SetValue("ge.storyProgressionSeen",true);
         telemExt = GetExtension(TelemetryExtension) as TelemetryExtension;
         telemExt.BeginTimedRegion("SPNT",TelemetryManager.SHOW_HIDE);
         CommunicationManager.SendUIMessage("ShowDialog",{
            "dialog_id":"FeatureDiscovery-StoryProgression",
            "type":DialogTypes.YES,
            "title":KeysGE.STORY_PROGRESSION_FEATURE_DISCOVERY_TITLE,
            "description":KeysGE.STORY_PROGRESSION_FEATURE_DISCOVERY_DESCRIPTION,
            "icon":GameTrayTunables.STORY_PROGRESSION_FEATURE_DISCOVERY_ICON,
            "dialogStyle":DialogTypes.STYLE_LARGE_ICON_TEXT_HORIZONTAL,
            "optionOneCallback":function():void
            {
               telemExt.EndTimedRegion("SPNT",TelemetryManager.SHOW_HIDE);
            }
         });
      }
      
      protected function ChangeGameStateToBuild(param1:int) : Boolean
      {
         var _loc2_:Boolean = GameStateFlags.IsBetweenStates;
         var _loc3_:Boolean = false;
         if(this.mGameState != GameStates.BUILD && !this.mbIsSaveLoadLocked && !_loc2_)
         {
            this.btnBuildBuy.Selected = true;
            (this.btnBuildBuy.GetExtension(FlairExtension) as FlairExtension).MarkAsSeen();
            UISettings.SessionSettings.SetValue("navMode",param1);
            _loc3_ = CommunicationManager.CallGameService("SetControlMode",{"mode":GameStates.BUILD},true) as Boolean;
            if(_loc3_)
            {
               CatalogData.Create();
            }
         }
         GameStateFlags.IsBetweenStates = _loc3_;
         return _loc3_;
      }
      
      protected function ChangeGameStateToLive() : void
      {
         var _loc1_:Boolean = GameStateFlags.IsBetweenStates;
         if(this.mGameState != GameStates.LIVEEDIT && this.mGameState != GameStates.PLAY && !_loc1_)
         {
            if(this.mGameState == GameStates.BUILD)
            {
               CommunicationManager.CallGameService("TriggerClientTutorial",ClientTutorialTrigger.BB_EXIT,true);
            }
            if(!this.IsLotFulfilled())
            {
               this.ShowLotUnfulfilledDialog();
            }
            else if(!this.IsVenueFulfilled())
            {
               this.ShowVenueConfirmationDialog(this.OnLiveModeClickConfirm);
            }
            else
            {
               this.OnLiveModeClickConfirm();
            }
         }
      }
      
      protected function OnLiveModeClickConfirm() : void
      {
         this.btnBuildBuy.Selected = false;
         var _loc1_:uint = this.mbIsWorldBuilder ? GameStates.LIVEEDIT : GameStates.PLAY;
         var _loc2_:Boolean = Boolean(CommunicationManager.CallGameService("SetControlMode",{"mode":_loc1_},true));
         GameStateFlags.IsBetweenStates = _loc2_;
         if(!_loc2_)
         {
            this.btnBuildBuy.Selected = true;
         }
      }
      
      protected function IsVenueFulfilled() : Boolean
      {
         var _loc6_:String = null;
         var _loc7_:Array = null;
         var _loc1_:Object = CommunicationManager.CallGameService("BBGetCurrentVenue") as Object;
         if(!_loc1_)
         {
            return true;
         }
         var _loc2_:Boolean = _loc1_["isFulfilled"] as Boolean;
         if(!_loc2_)
         {
            return false;
         }
         var _loc3_:String = _loc1_["venueKey"] as String;
         var _loc4_:Object = CommunicationManager.CallGameService("BBGetVenueInfo",{"venueKey":_loc3_});
         if(_loc4_)
         {
         }
         var _loc5_:VenueInfo = new VenueInfo(_loc4_);
         if(_loc5_.hasSubvenues || _loc5_.IsSubVenue())
         {
            _loc6_ = _loc5_.hasSubvenues ? _loc5_.tagKey : _loc5_.sourceVenueTagKey;
            _loc7_ = CommunicationManager.CallGameService("BBGetUnfulfilledSubvenues",{"venueKey":_loc6_}) as Array;
            return _loc7_.length == 0;
         }
         return _loc2_;
      }
      
      protected function IsLotFulfilled() : Boolean
      {
         var _loc1_:Object = CommunicationManager.CallGameService("BBGetRequirementsVenue") as Object;
         return _loc1_ ? _loc1_["isFulfilled"] as Boolean : true;
      }
      
      protected function ShowVenueConfirmationDialog(param1:Function) : void
      {
         CommunicationManager.SendUIMessage("ShowDialog",{
            "type":DialogTypes.YES_NO,
            "title":KeysBB.BB_LEAVE_INCOMPLETE_VENUE_CONFIRMATION.toString(),
            "optionOneText":Keys.GENERIC_OK.toString(),
            "optionOneCallback":param1,
            "closeText":Keys.GENERIC_CANCEL.toString()
         });
      }
      
      protected function ShowLotUnfulfilledDialog() : void
      {
         CommunicationManager.SendUIMessage("ShowDialog",{
            "type":DialogTypes.SINGLE_BUTTON,
            "title":KeysBB.BB_LEAVE_LOT_UNFULFILLED.toString(),
            "optionOneText":Keys.GENERIC_OK.toString(),
            "optionOneCallback":this.OnLotUnfulfilledConfirmed
         });
      }
      
      protected function OnLotUnfulfilledConfirmed() : void
      {
         var _loc1_:VenueInfo = BuildBuyStateData.RequirementsVenueInfo;
         if(!_loc1_)
         {
            return;
         }
         var _loc2_:ProductFilter = new ProductFilter();
         _loc2_.categoryTags = _loc1_.categoryTags;
         CommunicationManager.SendUIMessage("BBNavigateToFilter",_loc2_);
      }
      
      protected function ChangeGameStateToNeighborhood(param1:int) : void
      {
         if(this.mGameState != GameStates.LOT_SELECT && !this.mbIsSaveLoadLocked && !GameStateFlags.IsBetweenStates)
         {
            if(param1 == TransitionScreenMode.LIVE_TO_NHD_MAP_TRAVEL)
            {
               if(GameplayStateData.HasSims)
               {
                  CommunicationManager.SendMessage("SetAllowSimSwitch",false);
                  GameStateFlags.IsBetweenStates = CommunicationManager.CallGameService("GoToNeighborhoodTravel");
                  if(!GameStateFlags.IsBetweenStates)
                  {
                     CommunicationManager.SendMessage("SetAllowSimSwitch",true);
                  }
               }
            }
            else if(this.btnNeighborhood.enabled)
            {
               GameStateFlags.IsBetweenStates = true;
               CommunicationManager.CallGameService("ShowStateChangeLoad",param1);
            }
         }
      }
      
      protected function UpdateNeighborhoodButtonState() : void
      {
         var _loc1_:LocKey = null;
         var _loc2_:Boolean = false;
         var _loc3_:GameSaveLockUnlock = null;
         if(this.mGameState == GameStates.PLAY)
         {
            if(GameplayStateData.SaveLocked)
            {
               _loc3_ = GameplayStateData.SaveLockUnlockMessage;
               this.btnNeighborhood.enabled = false;
               this.btnNeighborhood.TooltipExt.SetText(_loc3_.lock_reason);
               return;
            }
            _loc2_ = !GameplayStateData.IsBlockingSituationRunning;
            this.btnNeighborhood.enabled = _loc2_;
            if(!_loc2_)
            {
               _loc1_ = Keys.ESCAPE_MENU_EDIT_WORLD_DISABLED_BY_EVENT;
            }
            else
            {
               _loc1_ = Keys.MODECONTROL_LIVE_GOTO_NEIGHBORHOOD;
            }
         }
         else
         {
            this.btnNeighborhood.enabled = true;
            _loc1_ = Keys.MODECONTROL_GOTO_NEIGHBORHOOD;
         }
         this.btnNeighborhood.TooltipExt.SetText(_loc1_);
      }
      
      protected function UpdateBuildBuyButtonState() : void
      {
         var _loc3_:BuildBuyLockUnlock = null;
         var _loc4_:VenueInfo = null;
         var _loc5_:LocKey = null;
         var _loc6_:uint = 0;
         var _loc1_:Button = this.btnBuildBuy;
         var _loc2_:uint = this.mGameState;
         _loc1_.enabled = true;
         _loc1_.mouseChildren = false;
         if(_loc2_ == GameStates.PLAY || _loc2_ == GameStates.LIVEEDIT)
         {
            _loc3_ = new BuildBuyLockUnlock(CommunicationManager.CallGameService("GetBBLockUnlock"));
            _loc1_.enabled = true;
            if(!this.mbIgnoreBuildBuyLockUnlock && _loc3_.build_buy_locked)
            {
               _loc1_.enabled = false;
               _loc1_.TooltipExt.SetText(_loc3_.reason);
            }
            else if(this.mbIsLotEditable)
            {
               (_loc1_.GetExtension(TooltipExtension) as TooltipExtension).SetText(Keys.MODECONTROL_BUILD);
            }
            else
            {
               _loc6_ = CommunicationManager.CallGameService("GetLotBuildBuyLock") as uint;
               switch(_loc6_)
               {
                  case BuildBuyLocks.LOT_TUNING:
                     _loc5_ = Keys.MODECONTROL_BUILD_DISABLED_RHLOT;
                     break;
                  case BuildBuyLocks.TRAVEL_GROUP:
                     _loc5_ = new LocKey(CommunicationManager.CallGameService("BBGetTravelGroupBuildDisabledMessage"));
                     break;
                  case BuildBuyLocks.UNIVERSITY_HOUSING:
                     _loc5_ = Keys.MODECONTROL_BUILD_DISABLED_UNIVERSITY_HOUSING;
                     break;
                  default:
                     _loc5_ = Keys.MODECONTROL_BUILD_DISABLED;
               }
               (_loc1_.GetExtension(TooltipExtension) as TooltipExtension).SetText(_loc5_);
               _loc1_.enabled = false;
            }
            _loc4_ = BuildBuyStateData.CurrentVenueInfo;
            if(Boolean(!BuildBuyStateData.IsLotOwnedByPlayer) && Boolean(_loc4_) && _loc4_.IsRetailLot)
            {
               _loc1_.TooltipExt.SetText(Keys.MODECONTROL_BUILD_DISABLED);
               _loc1_.enabled = false;
            }
            _loc1_.visible = true;
            this.btnNeighborhood.visible = _loc2_ == GameStates.PLAY;
         }
         else if(_loc2_ == GameStates.BUILD)
         {
            (_loc1_.GetExtension(TooltipExtension) as TooltipExtension).SetText(this.mbIsLotPlayable ? Keys.MODECONTROL_LIVE : Keys.MODECONTROL_LIVE_DISABLED);
            _loc1_.enabled = this.mbIsLotPlayable;
            _loc1_.visible = !this.mbShowNbhdButton;
            this.btnNeighborhood.visible = this.mbShowNbhdButton;
         }
         else
         {
            _loc1_.visible = this.btnNeighborhood.visible = false;
         }
         (_loc1_.GetExtension(TutorialTipExtension) as TutorialTipExtension).MarkVisibility(_loc1_.visible);
      }
      
      protected function UpdateStoreButtonState() : void
      {
         var _loc2_:GameSaveLockUnlock = null;
         var _loc1_:uint = CommunicationManager.CallGameService("GetGameState") as uint;
         if(TutorialMode.IsFTUE() || this.mbGuidanceActive)
         {
            this.DisableStoreButton(Keys.GAME_TRAY_TOOLTIP_STORE_DISABLED_BY_TUTORIAL);
            return;
         }
         if(_loc1_ == GameStates.PLAY)
         {
            if(GameplayStateData.SaveLocked)
            {
               _loc2_ = GameplayStateData.SaveLockUnlockMessage;
               this.DisableStoreButton(_loc2_.lock_reason);
               return;
            }
         }
         this.mBtnStore.enabled = true;
         if(SystemUtils.UsingController)
         {
            this.mBtnStore.TooltipExt.SetText(Keys.GAME_TRAY_TOOLTIP_STORE_NO_HOTKEY);
         }
         else
         {
            this.mBtnStore.TooltipExt.SetText(Keys.GAME_TRAY_TOOLTIP_STORE);
         }
         this.ShowStoreButtonNotificationIfNeeded();
      }
      
      protected function GetBundleDataObjectsForGameState(param1:Array) : Array
      {
         var _loc3_:Object = null;
         var _loc4_:Object = null;
         var _loc5_:Boolean = false;
         var _loc2_:Array = [];
         for each(_loc3_ in param1)
         {
            _loc4_ = _loc3_["gameStates"];
            if(!(!_loc4_ || _loc4_.length <= 0 || _loc3_.hasOwnProperty("buttonCta")))
            {
               _loc5_ = _loc4_.indexOf(this.mGameState) != -1;
               if((_loc5_) && _loc2_.indexOf(_loc3_) == -1)
               {
                  _loc2_.push(_loc3_);
               }
            }
         }
         return _loc2_;
      }
      
      protected function DisableStoreButton(param1:LocKey) : void
      {
         this.mBtnStore.ShowAlert(false);
         this.RemoveToaster();
         this.mBtnStore.enabled = false;
         this.mBtnStore.TooltipExt.SetText(param1);
      }
      
      protected function QueryLotState() : void
      {
         if(this.mGameState == GameStates.BUILD)
         {
            this.mbIsLotPlayable = CommunicationManager.CallGameService("IsLotPlayable") as Boolean;
            this.mbShowNbhdButton = CommunicationManager.CallGameService("ShouldSwitchBackToNhdFromBuild") as Boolean;
         }
         else if(this.mGameState == GameStates.LIVEEDIT || this.mGameState == GameStates.PLAY)
         {
            this.mbIsLotEditable = BuildBuyStateData.IsLotEditable;
         }
         this.mbIgnoreBuildBuyLockUnlock = CommunicationManager.CallGameService("IsForceFreeBuild",null,true) as Boolean;
      }
      
      public function RefreshFloorData(param1:Object = null) : void
      {
         var _loc2_:Object = CommunicationManager.CallGameService("BBGetLevelInfo",null,true);
         if(_loc2_)
         {
            this.mCurrentFloor = _loc2_["curLevel"];
            this.mMinLevel = _loc2_["minLevel"];
            this.mMaxLevel = _loc2_["maxLevel"];
            this.mbtnFloorUp.enabled = this.mCurrentFloor < this.mMaxLevel;
            this.mbtnFloorDown.enabled = this.mCurrentFloor > this.mMinLevel;
         }
         if(this.mGameState == GameStates.PLAY)
         {
            CommunicationManager.CallGameService("RefreshSkillBars",null,true);
         }
      }
      
      public function RefreshWallData(param1:Object = null) : void
      {
         var _loc2_:Button = null;
         if(param1 == null)
         {
            param1 = CommunicationManager.CallGameService("BBGetWallMode",null,true);
         }
         if(param1 is int)
         {
            this.mWallState = param1 as int;
            switch(this.mWallState)
            {
               case WallViewMode.WALLS_UP:
                  _loc2_ = this.btnWallsUp;
                  break;
               case WallViewMode.WALLS_DOWN:
                  _loc2_ = this.btnWallsDown;
                  break;
               case WallViewMode.WALLS_CUTAWAY:
                  _loc2_ = this.btnWallsCutaway;
            }
            _loc2_.Selected = true;
            this.btnWallsCutaway.visible = _loc2_ == this.btnWallsCutaway;
            this.btnWallsDown.visible = _loc2_ == this.btnWallsDown;
            this.btnWallsUp.visible = _loc2_ == this.btnWallsUp;
         }
      }
      
      protected function OnWallHeightClick(param1:PushButtonEvent) : void
      {
         var _loc2_:Button = param1.target as Button;
         var _loc3_:int = this.mWallButtons.indexOf(_loc2_);
         CommunicationManager.CallGameService("BBSetWallMode",_loc3_);
         this.mTelemetry.DispatchEvent(WALL_TELEMETRY_NAME_ID,TelemetryManager.SHOW_HIDE,null,[new TelemetryAttribute("type",this.mWallTelemtryLookUpTable[_loc3_])]);
         this.RefreshWallData();
         dispatchEvent(new Event(GenericEvent.CHANGE));
         this.btnWallsUp.dispatchEvent(new Event(GenericEvent.CHANGE));
      }
      
      protected function HandleShowCameraControl(param1:Object) : void
      {
         if(CommunicationManager.CallUIService("IsWidgetVisible","NotificationWall"))
         {
            CommunicationManager.SendUIMessage("HideNotificationWall",null);
            this.btnWall.Selected = false;
         }
         this.SelectGuidanceButton(false);
         dispatchEvent(new Event(GenericEvent.CHANGE));
      }
      
      protected function HandleShowNotificationWall(param1:Object) : void
      {
         this.CloseCameraControl();
         this.SelectGuidanceButton(false);
      }
      
      protected function HandleShowGuidanceTips(param1:Object) : void
      {
         if(Boolean(param1) && Boolean(param1.hasOwnProperty("showType")) && param1["showType"] == GuidanceTipsSharedTunables.PANE_SHOW_NOTHING)
         {
            this.SetScenarioButtonEnabled();
            return;
         }
         this.SelectNotificationWallButton(false);
         this.CloseCameraControl();
         this.SelectScenarioButton(false);
         this.btnScenario.enabled = false;
         this.btnScenario.TooltipExt.SetText(Keys.GAME_TRAY_TOOLTIP_GUIDANCE_DISABLED_ACTION);
      }
      
      protected function HandleOnlineAccessStateChanged(param1:Object) : void
      {
         var _loc3_:LocKey = null;
         if(this.mGameState == GameStates.UNKNOWN)
         {
            return;
         }
         this.SetGameState(this.mGameState);
         var _loc2_:Boolean = !(param1 as Boolean);
         this.btnShare.Selected = _loc2_;
         if(this.mGameState == GameStates.CAS && CASConfiguration.IsConfigured(CASConfiguration.CANNOT_USE_GALLERY))
         {
            _loc3_ = Keys.GAME_TRAY_TOOLTIP_CAS_DISABLED;
            this.btnShare.TooltipExt.SetText(_loc3_);
         }
         else
         {
            this.UpdateShareButtonEnabledTooltip();
         }
      }
      
      protected function HandleSituationChanged(param1:Object = null) : void
      {
         this.UpdateNeighborhoodButtonState();
         this.UpdateStoreButtonState();
      }
      
      protected function OnCASSubStateChanged() : void
      {
         var _loc2_:LocKey = null;
         var _loc1_:uint = CASStateData.GetCASSubState();
         if(_loc1_ == CASSubStates.PETPAINTING)
         {
            this.SelectNotificationWallButton(false);
            this.SelectScenarioButton(false);
            this.btnShare.enabled = false;
            this.btnShare.TooltipExt.SetText(KeysCAS.PAINTING_PANEL_DISABLED_TOOLTIP);
            this.btnSave.enabled = false;
            this.btnSave.TooltipExt.SetText(KeysCAS.PAINTING_PANEL_DISABLED_TOOLTIP);
            this.DisableStoreButton(KeysCAS.PAINTING_PANEL_DISABLED_TOOLTIP);
            this.btnWall.enabled = false;
            this.btnWall.TooltipExt.SetText(KeysCAS.PAINTING_PANEL_DISABLED_TOOLTIP);
            this.btnScenario.enabled = false;
            this.btnScenario.TooltipExt.SetText(KeysCAS.PAINTING_PANEL_DISABLED_TOOLTIP);
         }
         else if(_loc1_ == CASSubStates.STORIES || CASSubStates.AnyExpeditedSimState(_loc1_))
         {
            _loc2_ = CASSubStates.AnyExpeditedSimState(_loc1_) ? KeysCAS.CAS_STORIES_EXPEDITED_SIM_MODE_DISABLED_TOOLTIP : KeysCAS.CAS_STORIES_DISABLED_TOOLTIP;
            this.btnShare.enabled = false;
            this.btnShare.TooltipExt.SetText(_loc2_);
            this.btnSave.enabled = false;
            this.btnSave.TooltipExt.SetText(_loc2_);
            this.DisableStoreButton(_loc2_);
            this.btnGuidance.enabled = false;
            this.btnGuidance.TooltipExt.SetText(_loc2_);
            this.SelectNotificationWallButton(false);
            this.btnScenario.enabled = false;
            this.btnScenario.TooltipExt.SetText(_loc2_);
         }
         else
         {
            this.SetShareButtonEnabled();
            this.SetSaveButtonEnabled();
            this.UpdateStoreButtonState();
            this.btnWall.TooltipExt.SetText(Keys.GAME_TRAY_TOOLTIP_NOTIFICATION_WALL);
            this.btnWall.enabled = true;
            this.SetScenarioButtonEnabled();
            this.SetGuidanceButtonEnabled();
         }
      }
      
      protected function OnCASCatalogPanelFinishedAnimatingIn(param1:Object) : void
      {
         var _loc2_:WidgetBase = null;
         var _loc3_:Boolean = false;
         if(Boolean(param1) && "panelBounds" in param1)
         {
            if(Boolean(this.mcScenarioRequirementsPanel) && this.mcScenarioRequirementsPanel.visible)
            {
               if(this.mcScenarioRequirementsPanel.mcArrowBackground.getBounds(stage).intersects(param1.panelBounds))
               {
                  this.SelectScenarioButton(false);
               }
            }
            _loc2_ = LayoutAPI.GetLoadedWidgetByName("NotificationWall");
            if(Boolean(_loc2_) && _loc2_.visible)
            {
               _loc3_ = Boolean(CommunicationManager.CallUIService("NotificationWallOverlapsBounds",{"bounds":param1.panelBounds}));
               if(_loc3_)
               {
                  this.SelectNotificationWallButton(false);
               }
            }
         }
      }
      
      protected function OnShowGeneticsPanel(param1:Object) : void
      {
         this.btnShare.enabled = false;
         this.btnShare.TooltipExt.SetText(KeysCAS.GENETICS_DISABLED_TOOLTIP);
         this.DisableStoreButton(KeysCAS.GENETICS_DISABLED_TOOLTIP);
         this.btnGuidance.enabled = false;
         this.btnGuidance.TooltipExt.SetText(KeysCAS.GENETICS_DISABLED_TOOLTIP);
         CommunicationManager.SendUIMessage("ShowGuidanceTips",{"showType":GuidanceTipsSharedTunables.PANE_SHOW_NOTHING});
         this.mbGeneticsPaneActive = true;
      }
      
      protected function OnHideGeneticsPanel(param1:Object) : void
      {
         this.SetShareButtonEnabled();
         this.UpdateStoreButtonState();
         this.SetGuidanceButtonEnabled();
         this.mbGeneticsPaneActive = false;
      }
      
      protected function OnShowSeasonSelect(param1:Object) : void
      {
         this.btnShare.enabled = false;
         this.btnShare.TooltipExt.SetText(KeysGE.NHD_NOT_AVAILABLE_WHILE_SELECTING_SEASON);
         this.btnWall.enabled = false;
         this.btnWall.TooltipExt.SetText(KeysGE.NHD_NOT_AVAILABLE_WHILE_SELECTING_SEASON);
         this.btnManageHH.enabled = false;
         this.btnManageHH.TooltipExt.SetText(KeysGE.NHD_NOT_AVAILABLE_WHILE_SELECTING_SEASON);
         this.btnGuidance.enabled = false;
         this.btnManageHH.TooltipExt.SetText(KeysGE.NHD_NOT_AVAILABLE_WHILE_SELECTING_SEASON);
         this.DisableStoreButton(KeysGE.NHD_NOT_AVAILABLE_WHILE_SELECTING_SEASON);
         if(this.btnFreeTrialTimer.visible)
         {
            this.btnFreeTrialTimer.enabled = false;
            this.btnFreeTrialTimer.TooltipExt.SetText(KeysGE.NHD_NOT_AVAILABLE_WHILE_SELECTING_SEASON);
            this.btnFreeTrialTimer.TooltipExt.UseHitAreaBounds = true;
         }
      }
      
      protected function OnHideSeasonSelect(param1:Object) : void
      {
         this.SetShareButtonEnabled();
         this.UpdateBuildBuyButtonState();
         this.UpdateStoreButtonState();
         this.btnWall.enabled = true;
         this.btnWall.TooltipExt.SetText(Keys.GAME_TRAY_TOOLTIP_NOTIFICATION_WALL);
         var _loc2_:GENeighborhoodStateManager = GENeighborhoodStateManager.getInstance();
         this.UpdateHHManagementButton(_loc2_.Mode);
         this.btnGuidance.enabled = true;
         if(this.btnFreeTrialTimer.visible)
         {
            this.btnFreeTrialTimer.enabled = true;
            this.btnFreeTrialTimer.TooltipExt.SetText(null);
         }
      }
      
      protected function SetGameState(param1:uint) : void
      {
         var _loc3_:String = null;
         var _loc5_:* = undefined;
         var _loc2_:String = this.GetFrameState(param1);
         if(_loc2_)
         {
            visible = true;
            gotoAndStop(_loc2_);
            if(SystemUtils.UsingConsoleInputMode)
            {
               for(_loc5_ in this.mButtonToFrameMapping)
               {
                  _loc5_.visible = !SystemUtils.UsingController || this.mButtonToFrameMapping[_loc5_].indexOf(_loc2_) >= 0;
               }
               if(this.btnFreeTrialTimer)
               {
                  this.btnFreeTrialTimer.visible = false;
               }
            }
            switch(param1)
            {
               case GameStates.MAIN_MENU:
                  this.btnWall.EnableStatePrefix("mm");
                  this.btnShare.EnableStatePrefix("mm");
                  this.btnShare.DisableStatePrefix("full");
                  this.btnWall.TooltipExt.SetText(Keys.GAME_TRAY_TOOLTIP_NOTIFICATION_WALL);
                  break;
               case GameStates.LOT_SELECT:
               case GameStates.TRAVEL:
                  this.btnShare.EnableStatePrefix("full");
                  this.btnShare.DisableStatePrefix("mm");
                  this.btnWall.DisableStatePrefix("mm");
                  break;
               default:
                  this.btnShare.DisableStatePrefix("full");
                  this.btnShare.DisableStatePrefix("mm");
                  this.btnWall.DisableStatePrefix("mm");
            }
            if(param1 == GameStates.BUILD)
            {
               _loc3_ = TutorialTipUIElement.BB_GALLERY_BUTTON;
            }
            else if(param1 == GameStates.CAS)
            {
               _loc3_ = TutorialTipUIElement.CAS_GALLERY_SAVE_BUTTON;
               this.SetSaveButtonEnabled();
               if(CASConfiguration.IsConfigured(CASConfiguration.CANNOT_USE_GALLERY))
               {
                  this.btnShare.enabled = false;
                  this.btnShare.TooltipExt.SetText(Keys.GAME_TRAY_TOOLTIP_CAS_DISABLED);
               }
            }
            else if(param1 == GameStates.PLAY)
            {
               _loc3_ = TutorialTipUIElement.CAS_GALLERY_BUTTON;
            }
         }
         else
         {
            visible = false;
         }
         if(param1 == GameStates.BUILD || param1 == GameStates.PLAY)
         {
            this.HandleSituationChanged(null);
         }
         var _loc4_:TutorialTipExtension = this.btnShare.GetExtension(TutorialTipExtension,false) as TutorialTipExtension;
         if(_loc3_)
         {
            if(_loc4_)
            {
               _loc4_.MarkVisibility(this.btnShare.visible);
            }
            else
            {
               _loc4_ = this.btnShare.GetExtension(TutorialTipExtension) as TutorialTipExtension;
               _loc4_.AddSatisfactionEvent(PushButtonEvent.CLICK);
               _loc4_.ShouldHideImmediatelyOnSatisfy = true;
            }
            _loc4_.ControlEnum = _loc3_;
         }
         else if(_loc4_)
         {
            _loc4_.MarkVisibility(false);
         }
         if(SystemUtils.UsingController)
         {
            dispatchEvent(new Event(CONTROL_PANEL_GAME_STATE_SET));
         }
         if(param1 != GameStates.PLAY)
         {
            CommunicationManager.SendUIMessage("PlayModeLeft");
         }
         if(this.mbStoreEnabled && Boolean(this.btnShare["mcBackground"]))
         {
            this.btnShare["mcBackground"].gotoAndStop("crescent");
         }
         this.mGameState = param1;
      }
      
      protected function GetFrameState(param1:uint) : String
      {
         var _loc6_:Boolean = false;
         var _loc7_:String = null;
         var _loc8_:String = null;
         var _loc9_:String = null;
         var _loc2_:String = null;
         var _loc3_:Boolean = false;
         var _loc4_:Boolean = CommunicationManager.CallGameService("GuidanceEnabled") as Boolean;
         var _loc5_:Boolean = false;
         switch(param1)
         {
            case GameStates.CAS:
               _loc6_ = CommunicationManager.CallGameService("GetCurrentScenario") != null;
               if(_loc6_)
               {
                  _loc2_ = "cas_scenario";
               }
               else
               {
                  _loc2_ = "cas";
               }
               if(_loc4_)
               {
                  _loc5_ = CommunicationManager.CallGameService("GuidanceCASForceDisabled") as Boolean;
               }
               break;
            case GameStates.MAIN_MENU:
               _loc2_ = "main_menu";
               if(SystemUtils.UsingConsoleInputMode)
               {
                  _loc3_ = true;
               }
               break;
            case GameStates.LIVEEDIT:
               _loc2_ = "world_builder";
               if(_loc4_)
               {
                  _loc5_ = CommunicationManager.CallGameService("GuidanceWorldForceDisabled") as Boolean;
               }
               break;
            case GameStates.PLAY:
               _loc2_ = "live";
               if(_loc4_)
               {
                  _loc5_ = CommunicationManager.CallGameService("GuidanceLiveForceDisabled") as Boolean;
               }
               break;
            case GameStates.LOT_SELECT:
               _loc2_ = "nbhd";
               if(_loc4_)
               {
                  _loc5_ = CommunicationManager.CallGameService("GuidanceLotForceDisabled") as Boolean;
               }
               break;
            case GameStates.TRAVEL:
               _loc2_ = "travel";
               break;
            case GameStates.BUILD:
               if(this.mbShowNbhdButton)
               {
                  _loc2_ = "build_from_nbhd";
               }
               else
               {
                  _loc2_ = "build_from_live";
               }
               if(_loc4_)
               {
                  _loc5_ = CommunicationManager.CallGameService("GuidanceBBForceDisabled") as Boolean;
               }
               break;
            default:
               _loc2_ = null;
         }
         if(Boolean(_loc2_) && Boolean(_loc4_) && !_loc5_)
         {
            _loc7_ = _loc2_ + "_guidance";
            if(this.mFrameLabels[_loc7_])
            {
               _loc2_ = _loc7_;
            }
         }
         if(Boolean(_loc2_) && (SystemUtils.UsingController || _loc3_))
         {
            _loc8_ = "controller_" + _loc2_;
            if(this.mFrameLabels[_loc8_])
            {
               _loc2_ = _loc8_;
            }
         }
         if(Boolean(_loc2_) && this.mbStoreEnabled)
         {
            _loc9_ = _loc2_ + "_store";
            if(this.mFrameLabels[_loc9_])
            {
               _loc2_ = _loc9_;
            }
         }
         return _loc2_;
      }
      
      protected function SetShareButtonEnabled() : void
      {
         if(this.mGameState == GameStates.CAS && CASConfiguration.IsConfigured(CASConfiguration.CANNOT_USE_GALLERY))
         {
            this.btnShare.enabled = false;
            this.btnShare.TooltipExt.SetText(Keys.GAME_TRAY_TOOLTIP_CAS_DISABLED);
            return;
         }
         if(this.mbIsCFEBuild)
         {
            this.btnShare.enabled = false;
            this.btnShare.TooltipExt.SetText(Keys.GAME_TRAY_TOOLTIP_SHARE_CFE_DISABLED);
            return;
         }
         if(TutorialMode.IsFTUE() || this.mbGuidanceActive)
         {
            this.btnShare.enabled = false;
            this.btnShare.TooltipExt.SetText(Keys.GAME_TRAY_TOOLTIP_GALLERY_TUTORIAL_DISABLED);
            return;
         }
         this.btnShare.enabled = true;
         this.UpdateShareButtonEnabledTooltip();
      }
      
      protected function UpdateShareButtonEnabledTooltip() : void
      {
         var _loc1_:LocKey = null;
         if(ConnectionManager.IsOnlineAccessDisabled)
         {
            _loc1_ = Keys.GAME_TRAY_TOOLTIP_LIBRARY;
         }
         else if(SystemUtils.UsingController)
         {
            _loc1_ = Keys.GAME_TRAY_TOOLTIP_SHARE_NO_HOTKEY;
         }
         else
         {
            _loc1_ = Keys.GAME_TRAY_TOOLTIP_SHARE;
         }
         this.btnShare.TooltipExt.SetText(_loc1_);
      }
      
      protected function SetSaveButtonEnabled() : void
      {
         if(this.mbIsCFEBuild)
         {
            this.btnSave.enabled = false;
            this.btnSave.TooltipExt.SetText(Keys.GAME_TRAY_TOOLTIP_SHARE_CFE_DISABLED);
            return;
         }
         if(CASStateData.GetCASSubState() == CASSubStates.STORIES || CASSubStates.AnyExpeditedSimState(CASStateData.GetCASSubState()))
         {
            this.btnSave.enabled = false;
            this.btnSave.TooltipExt.SetText(CASSubStates.AnyExpeditedSimState(CASStateData.GetCASSubState()) ? KeysCAS.CAS_STORIES_EXPEDITED_SIM_MODE_DISABLED_TOOLTIP : KeysCAS.CAS_STORIES_DISABLED_TOOLTIP);
            return;
         }
         if(TutorialMode.IsFTUE() || this.mbGuidanceActive)
         {
            this.btnSave.enabled = false;
            this.btnSave.TooltipExt.SetText(Keys.GAME_TRAY_TOOLTIP_FTUE_HOUSEHOLD_SAVE_DISABLED);
            return;
         }
         if(this.mGameState == GameStates.CAS && CASConfiguration.IsConfigured(CASConfiguration.CANNOT_SAVE))
         {
            this.btnSave.enabled = false;
            this.btnSave.TooltipExt.SetText(Keys.GAME_TRAY_TOOLTIP_CAS_DISABLED);
            return;
         }
         this.btnSave.enabled = true;
         this.btnSave.TooltipExt.SetText(Keys.GAME_TRAY_TOOLTIP_HOUSEHOLD_SAVE);
      }
      
      protected function HandleGuidanceItemActionActive() : void
      {
         this.mbGuidanceActive = true;
         if(this.btnGuidance.enabled)
         {
            this.btnGuidance.enabled = false;
            this.btnGuidance.TooltipExt.SetText(Keys.GAME_TRAY_TOOLTIP_GUIDANCE_DISABLED_ACTION);
         }
         this.SetSaveButtonEnabled();
         this.SetShareButtonEnabled();
         this.UpdateStoreButtonState();
         this.btnScenario.enabled = false;
         this.btnScenario.TooltipExt.SetText(Keys.GAME_TRAY_TOOLTIP_GUIDANCE_DISABLED_ACTION);
      }
      
      protected function HandleGuidanceItemActionInactive() : void
      {
         this.mbGuidanceActive = false;
         if(CASStateData.GetCASSubState() == CASSubStates.NONE)
         {
            this.SetGuidanceButtonEnabled();
         }
         this.SetSaveButtonEnabled();
         this.SetShareButtonEnabled();
         this.UpdateStoreButtonState();
         this.SetScenarioButtonEnabled();
      }
      
      protected function HandleGuidanceHelpCenterClosed() : void
      {
         this.SelectGuidanceButton(false,true);
         this.SetScenarioButtonEnabled();
      }
      
      protected function HandleGuidanceItemShown() : void
      {
         this.SelectGuidanceButton(true,true);
      }
      
      protected function HandleGuidanceItemHidden() : void
      {
         this.SelectGuidanceButton(false,true);
         if(currentFrameLabel == "cas_scenario_guidance")
         {
            this.SelectScenarioButton(true);
         }
      }
      
      protected function SetGuidanceButtonEnabled(param1:Boolean = false) : void
      {
         if(this.mGameState == GameStates.CAS && CASConfiguration.CurrentConfiguration != CASConfiguration.CONFIG_DEFAULT_CAS)
         {
            this.btnGuidance.enabled = false;
            this.btnGuidance.TooltipExt.SetText(Keys.GAME_TRAY_TOOLTIP_CAS_DISABLED);
         }
         else if(this.mbGuidanceActive && !param1)
         {
            this.btnGuidance.enabled = false;
            this.btnGuidance.TooltipExt.SetText(Keys.GAME_TRAY_TOOLTIP_GUIDANCE_DISABLED_ACTION);
         }
         else
         {
            this.btnGuidance.enabled = true;
            this.btnGuidance.TooltipExt.SetText(Keys.GAME_TRAY_TOOLTIP_GUIDANCE);
         }
      }
      
      protected function HandleControlPanelRefresh(param1:Object) : void
      {
         var _loc2_:Number = NaN;
         this.SetGameState(this.mGameState);
         if(this.mcScenarioRequirementsPanel != null && this.mcScenarioRequirementsPanel.visible)
         {
            _loc2_ = this.btnScenario.x + this.btnScenario.hitArea.width / 2;
            this.mcScenarioRequirementsPanel.mcArrow.x = _loc2_ - this.mcScenarioRequirementsPanel.x - ScenarioTunables.SCENARIO_REQUIREMENTS_LIST_BACKGROUND_ARROW_OFFSET;
         }
      }
      
      protected function SetupHelpTab() : void
      {
         if(SystemUtils.IsPS4)
         {
            this.mcHelpTab.mcHelpIcon.gotoAndStop("ps4");
         }
         else if(SystemUtils.IsXB1)
         {
            this.mcHelpTab.mcHelpIcon.gotoAndStop("xb1");
         }
         this.mcHelpTab.txtControls.autoSize = TextFieldAutoSize.RIGHT;
         this.mcHelpTab.mcHelpIcon.x = this.mcHelpTab.txtControls.x - this.mcHelpTab.mcHelpIcon.mcButtonIcon.width / 2 - GameTrayTunables.HELP_ICON_TO_TEXT_PADDING;
      }
      
      public function HandleInputToggled() : void
      {
         var _loc1_:uint = CommunicationManager.CallGameService("GetGameState",null) as uint;
         this.SetGameState(_loc1_);
         this.mcHelpTab.visible = SystemUtils.UsingController && Boolean(CommunicationManager.CallGameService("OptionsGetValue",{"name":"ControlReminderEnabled"}));
         this.CloseCameraControl();
         this.btnCamera.TooltipExt.SetText(SystemUtils.UsingController ? KeysConsole.FREE_CAM : KeysGP.CAMERA_CONTROLS);
         if(!SystemUtils.UsingController)
         {
            this.RefreshWallData();
         }
         if(this.btnGuidance.enabled && CommunicationManager.CallUIService("IsWidgetVisible","GuidanceTips") == true)
         {
            CommunicationManager.SendUIMessage("ShowGuidanceTips",{"showType":GuidanceTipsSharedTunables.PANE_SHOW_WINDOW_POSITION_CHANGED});
         }
         if(this.btnShare.enabled)
         {
            this.UpdateShareButtonEnabledTooltip();
         }
         if(this.mBtnStore)
         {
            this.UpdateStoreButtonState();
         }
      }
      
      protected function HandleShowControlHelpPane(param1:Object) : void
      {
         this.mcHelpTab.visible = param1 as Boolean;
      }
      
      internal function frame1() : *
      {
         stop();
      }
      
      internal function frame5() : *
      {
         stop();
      }
      
      internal function frame9() : *
      {
         stop();
      }
      
      internal function frame14() : *
      {
         stop();
      }
      
      internal function frame19() : *
      {
         stop();
      }
      
      internal function frame28() : *
      {
         stop();
      }
      
      internal function frame34() : *
      {
         stop();
      }
      
      internal function frame40() : *
      {
         stop();
      }
      
      internal function frame46() : *
      {
         stop();
      }
      
      internal function frame53() : *
      {
         stop();
      }
      
      internal function frame59() : *
      {
         stop();
      }
      
      internal function frame66() : *
      {
         stop();
      }
      
      internal function frame78() : *
      {
         stop();
      }
      
      internal function frame91() : *
      {
         stop();
      }
      
      internal function frame104() : *
      {
         stop();
      }
      
      internal function frame117() : *
      {
         stop();
      }
      
      internal function frame132() : *
      {
         stop();
      }
      
      internal function frame137() : *
      {
         stop();
      }
      
      internal function frame142() : *
      {
         stop();
      }
      
      internal function frame147() : *
      {
         stop();
      }
      
      internal function frame152() : *
      {
         stop();
      }
      
      internal function frame160() : *
      {
         stop();
      }
      
      internal function frame166() : *
      {
         stop();
      }
      
      internal function frame173() : *
      {
         stop();
      }
      
      internal function frame179() : *
      {
         stop();
      }
      
      internal function frame186() : *
      {
         stop();
      }
      
      internal function frame192() : *
      {
         stop();
      }
      
      internal function frame198() : *
      {
         stop();
      }
      
      internal function frame209() : *
      {
         stop();
      }
      
      internal function frame222() : *
      {
         stop();
      }
      
      internal function frame235() : *
      {
         stop();
      }
      
      internal function frame248() : *
      {
         stop();
      }
      
      internal function frame262() : *
      {
         stop();
      }
      
      internal function frame267() : *
      {
         stop();
      }
      
      internal function frame271() : *
      {
         stop();
      }
      
      internal function frame276() : *
      {
         stop();
      }
      
      internal function frame281() : *
      {
         stop();
      }
      
      internal function frame290() : *
      {
         stop();
      }
      
      internal function frame296() : *
      {
         stop();
      }
      
      internal function frame302() : *
      {
         stop();
      }
      
      internal function frame308() : *
      {
         stop();
      }
      
      internal function frame315() : *
      {
         stop();
      }
      
      internal function frame321() : *
      {
         stop();
      }
      
      internal function frame328() : *
      {
         stop();
      }
      
      internal function frame340() : *
      {
         stop();
      }
      
      internal function frame353() : *
      {
         stop();
      }
      
      internal function frame366() : *
      {
         stop();
      }
      
      internal function frame379() : *
      {
         stop();
      }
      
      internal function frame394() : *
      {
         stop();
      }
      
      internal function frame399() : *
      {
         stop();
      }
      
      internal function frame404() : *
      {
         stop();
      }
      
      internal function frame409() : *
      {
         stop();
      }
      
      internal function frame414() : *
      {
         stop();
      }
      
      internal function frame422() : *
      {
         stop();
      }
      
      internal function frame428() : *
      {
         stop();
      }
      
      internal function frame435() : *
      {
         stop();
      }
      
      internal function frame441() : *
      {
         stop();
      }
      
      internal function frame448() : *
      {
         stop();
      }
      
      internal function frame454() : *
      {
         stop();
      }
      
      internal function frame460() : *
      {
         stop();
      }
      
      internal function frame471() : *
      {
         stop();
      }
      
      internal function frame484() : *
      {
         stop();
      }
      
      internal function frame497() : *
      {
         stop();
      }
      
      internal function frame510() : *
      {
         stop();
      }
      
      internal function frame524() : *
      {
         stop();
      }
   }
}

