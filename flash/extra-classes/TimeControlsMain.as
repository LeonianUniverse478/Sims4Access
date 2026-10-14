package widgets.TimeControls
{
   import flash.display.DisplayObject;
   import flash.display.MovieClip;
   import flash.events.MouseEvent;
   import flash.geom.Rectangle;
   import flash.text.TextField;
   import flash.text.TextFieldAutoSize;
   import flash.utils.getDefinitionByName;
   import gamedata.GameContent;
   import gamedata.Gameplay.shared.EcoFootprint;
   import gamedata.Gameplay.shared.GameplayStateData;
   import gamedata.shared.GameClockTime;
   import olympus.audio.Audio;
   import olympus.constants.ActionCodes;
   import olympus.constants.GameStates;
   import olympus.constants.InputActionPriorities;
   import olympus.constants.KeyCodes;
   import olympus.controllers.SelectableGroup;
   import olympus.core.Ticker;
   import olympus.core.Time;
   import olympus.core.widget.WidgetBase;
   import olympus.events.PushButtonEvent;
   import olympus.events.TickerEvent;
   import olympus.extensions.GoalExtension;
   import olympus.extensions.InputModeVisibilityExtension;
   import olympus.extensions.TutorialTipExtension;
   import olympus.gui.buttons.Button;
   import olympus.input.InputAction;
   import olympus.input.InputTrigger;
   import olympus.io.CommunicationManager;
   import olympus.io.EventManager;
   import olympus.io.InputActionManager;
   import olympus.localization.Keys;
   import olympus.localization.KeysConsole;
   import olympus.localization.KeysGP;
   import olympus.localization.LocKey;
   import olympus.math.TimeSpan;
   import olympus.utils.SystemUtils;
   import widgets.Gameplay.SimInfoHUD.SimInfoTray.constants.SimInfoTrayTunables;
   import widgets.TimeControls.constants.TimeControlsTunables;
   import widgets.shared.constants.GlobalTunables;
   import widgets.shared.constants.TutorialTipUIElement;
   import widgets.shared.controls.Console.LegendIcon;
   
   public class TimeControlsMain extends WidgetBase
   {
      
      protected static const CAM_BUTTON_PREFIX_MAP:Object = {
         "none":[""],
         "selected":["selected_",""],
         "recording":["recording_",""],
         "recording_selected":["recording_selected_",""]
      };
      
      protected static const FRAME_DEFAULT:* = "default";
      
      protected static const FRAME_WEATHER_SEASON_ECO:* = "weather_season_eco";
      
      protected static const FRAME_WEATHER_SEASON:* = "weather_season";
      
      protected static const FRAME_ECO_FOOTPRINT:* = "eco";
      
      protected static const FRAME_WEATHER:* = "weather";
      
      protected static const FRAME_WEATHER_ECO:* = "weather_eco";
      
      public static var TIME_TICK_BACKWARDS_THRESHOLD:uint = 120000;
      
      public var btnPause:Button;
      
      public var btnSpeedOne:Button;
      
      public var btnSpeedTwo:Button;
      
      public var btnSpeedThree:Button;
      
      public var txtGameTime:TextField;
      
      public var txtTimeSpeedName:TextField;
      
      public var mcBlurEffect:MovieClip;
      
      public var mcGameSpeedSlow:MovieClip;
      
      public var mcGameSpeedFast:MovieClip;
      
      public var mcCameraPanel:CameraPanel;
      
      public var btnCameraOptions:Button;
      
      public var mcDividingLine:MovieClip;
      
      protected var mCurrentTime:TimeSpan;
      
      protected var mTimeButtonGroup:SelectableGroup;
      
      protected var mTimeButtonArray:Array = new Array();
      
      protected var mCurrentDisplayedTimeMilliseconds:uint = 0;
      
      protected var mbSuperSpeedEnabled:Boolean;
      
      protected var mInputActionCloseCameraPanel:InputAction;
      
      protected var mLegendIconSlow:LegendIcon;
      
      protected var mLegendIconFast:LegendIcon;
      
      protected var mInputActionSpeedControls:Array;
      
      protected var mInputActionIncreaseGameSpeed:InputAction;
      
      protected var mInputActionDecreaseGameSpeed:InputAction;
      
      protected var mInputActionIncreaseGameSpeedFreeCam:InputAction;
      
      protected var mInputActionDecreaseGameSpeedFreeCam:InputAction;
      
      protected var mbGamepadTimeControlsEnabled:Boolean = true;

      protected var mA11yTimeHovered:Boolean = false;

      public function TimeControlsMain()
      {
         this.mInputActionSpeedControls = [InputAction.WhenTriggered(InputTrigger.FromKeyBinding(KeyCodes.TILDE)).CallFunction(this.OnPauseClick).RestrictToGameStates(GameStates.PLAY).SetLowPriority(true),InputAction.WhenTriggered(InputTrigger.FromKeyBinding(KeyCodes.ZERO)).CallFunction(this.OnPauseClick).RestrictToGameStates(GameStates.PLAY).SetLowPriority(true),InputAction.WhenTriggered(InputTrigger.FromKeyBinding(KeyCodes.NUMPAD_0)).CallFunction(this.OnPauseClick).RestrictToGameStates(GameStates.PLAY).SetLowPriority(true),InputAction.WhenTriggered(InputTrigger.FromKeyBinding(KeyCodes.ONE)).CallFunction(this.OnSpeedOneClick).RestrictToGameStates(GameStates.PLAY).SetLowPriority(true),InputAction.WhenTriggered(InputTrigger.FromKeyBinding(KeyCodes.NUMPAD_1)).CallFunction(this.OnSpeedOneClick).RestrictToGameStates(GameStates.PLAY).SetLowPriority(true),InputAction.WhenTriggered(InputTrigger.FromKeyBinding(KeyCodes.TWO)).CallFunction(this.OnSpeedTwoClick).RestrictToGameStates(GameStates.PLAY).SetLowPriority(true)
         ,InputAction.WhenTriggered(InputTrigger.FromKeyBinding(KeyCodes.NUMPAD_2)).CallFunction(this.OnSpeedTwoClick).RestrictToGameStates(GameStates.PLAY).SetLowPriority(true),InputAction.WhenTriggered(InputTrigger.FromKeyBinding(KeyCodes.THREE)).CallFunction(this.OnSpeedThreeClick).RestrictToGameStates(GameStates.PLAY).SetLowPriority(true),InputAction.WhenTriggered(InputTrigger.FromKeyBinding(KeyCodes.NUMPAD_3)).CallFunction(this.OnSpeedThreeClick).RestrictToGameStates(GameStates.PLAY).SetLowPriority(true)];
         addFrameScript(7,this.frame8,20,this.frame21,31,this.frame32,42,this.frame43,53,this.frame54,64,this.frame65);
         super();
      }
      
      override public function Initialize() : void
      {
         var _loc1_:SelectableGroup = null;
         super.Initialize();
         this.SetKeyFrame();
         AddMessageListener("EcoLivingOptionsChanged",this.SetKeyFrame);
         _loc1_ = new SelectableGroup();
         var _loc2_:Button = this.btnPause;
         _loc2_.addEventListener(PushButtonEvent.CLICK,this.OnPauseClick,false,0,true);
         _loc2_.TooltipExt.SetText(KeysGP.TIME_CONTROLS_BTN_PAUSE);
         _loc2_.AudioExt.ElementName = "PauseButton";
         _loc1_.Add(_loc2_,true);
         this.mTimeButtonArray.push(_loc2_);
         _loc2_ = this.btnSpeedOne;
         _loc2_.addEventListener(PushButtonEvent.CLICK,this.OnSpeedOneClick,false,0,true);
         _loc2_.TooltipExt.SetText(KeysGP.TIME_CONTROLS_BTN_SPEED_ONE);
         _loc2_.AudioExt.ElementName = "SpeedOneButton";
         _loc1_.Add(_loc2_,true);
         this.mTimeButtonArray.push(_loc2_);
         _loc2_ = this.btnSpeedTwo;
         _loc2_.addEventListener(PushButtonEvent.CLICK,this.OnSpeedTwoClick,false,0,true);
         _loc2_.TooltipExt.SetText(KeysGP.TIME_CONTROLS_BTN_SPEED_TWO);
         _loc2_.AudioExt.ElementName = "SpeedTwoButton";
         _loc1_.Add(_loc2_,true);
         this.mTimeButtonArray.push(_loc2_);
         _loc2_ = this.btnSpeedThree;
         _loc2_.addEventListener(PushButtonEvent.CLICK,this.OnSpeedThreeClick,false,0,true);
         _loc2_.TooltipExt.SetText(KeysGP.TIME_CONTROLS_BTN_SPEED_THREE);
         _loc2_.AudioExt.ElementName = "SpeedThreeButton";
         _loc1_.Add(_loc2_,true);
         this.mTimeButtonArray.push(_loc2_);
         var _loc3_:TutorialTipExtension = this.btnSpeedThree.GetExtension(TutorialTipExtension) as TutorialTipExtension;
         _loc3_.ControlEnum = TutorialTipUIElement.LIVE_TIME_SPEED3_CONTROL;
         var _loc4_:GoalExtension = GoalExtension.Get(this.btnSpeedThree);
         _loc4_.ControlEnum = TutorialTipUIElement.LIVE_TIME_SPEED3_CONTROL;
         _loc4_.AddSatisfactionEvent(PushButtonEvent.CLICK);
         _loc2_ = this.btnCameraOptions;
         _loc2_.addEventListener(PushButtonEvent.CLICK,this.OnCameraOptionsClick,false,0,true);
         _loc2_.TooltipExt.SetText(KeysGP.TIME_CONTROLS_BTN_CAMERA);
         _loc2_.AudioExt.ElementName = "CameraOptions";
         _loc2_.PrefixMap = CAM_BUTTON_PREFIX_MAP;
         this.mcCameraPanel.visible = false;
         this.mcCameraPanel.stop();
         this.UpdateAudioEvents(Time.mGameSpeed);
         this.mTimeButtonGroup = _loc1_;
         this.txtTimeSpeedName.htmlText = Keys.GENERIC_PAUSE.toString();
         this.txtGameTime.autoSize = TextFieldAutoSize.CENTER;
         // a11y: EA sets both of these mouseEnabled = false, which leaves the
         // clock area with NO hit surface at all; verified 2026-08-03 by
         // probe, where MOUSE_OVER only ever fired over the speed/camera
         // buttons and never over the clock. Without a hit surface the clock
         // text can never be hovered, so it could never be narrated. Giving
         // the fields their own hit surface costs nothing visually: they are
         // not selectable, they sit clear of the buttons, and mouse events
         // still bubble to the panel.
         this.txtTimeSpeedName.mouseEnabled = true;
         this.txtGameTime.mouseEnabled = true;
         AddMessageListener("UpdateGameClock",this.HandleUpdateGameClock,GameClockTime);
         AddMessageListener("ToggleVideoRecord",this.HandleToggleVideoRecord);
         AddMessageListener("IncreaseGameSpeed",this.IncreaseGameSpeed);
         AddMessageListener("DecreaseGameSpeed",this.DecreaseGameSpeed);
         if(SystemUtils.UsingConsoleInputMode)
         {
            AddMessageListener("DisableGamepadTimeControls",this.DisableGamepadTimeControls);
            AddMessageListener("EnableGamepadTimeControls",this.EnableGamepadTimeControls);
            CommunicationManager.RegisterServiceHandler("CanChangeGameSpeed",this.HandleCanChangeGameSpeed,this);
         }
         Ticker.Add(this,0,this.Update);
         this.mcBlurEffect.stop();
         this.mcBlurEffect.visible = false;
         this.mbSuperSpeedEnabled = false;
         this.UpdateTimeText(Time.GetGameTime());
         this.RefreshGameClock();
         var _loc5_:TutorialTipExtension = GetExtension(TutorialTipExtension) as TutorialTipExtension;
         _loc5_.ControlEnum = TutorialTipUIElement.LIVE_TIME_CONTROLS;
         if(SystemUtils.UsingConsoleInputMode)
         {
            _loc5_.AddSatisfactionMessage("IncreaseGameSpeed");
            _loc5_.AddSatisfactionMessage("DecreaseGameSpeed");
         }
         this.mInputActionCloseCameraPanel = InputAction.WhenTriggered(InputTrigger.FromKeyBinding(KeyCodes.ESC)).CallFunction(this.CloseCameraPanel).SetPriority(InputActionPriorities.ESC_PIE_MENU);
         // a11y: the clock text (txtGameTime) is mouseEnabled=false, so the
         // generic hover narration can never see it. Announce the panel's own
         // line (day + time, plus "Paused" when shown) whenever the pointer
         // enters the panel outside its buttons; Python holds the forecast
         // pop-up back behind it (a11y.timewidget_enc).
         addEventListener(MouseEvent.MOUSE_OVER,this.A11yOnTimeOver,false,0,true);
         addEventListener(MouseEvent.ROLL_OUT,this.A11yOnTimeOut,false,0,true);
         this.A11yAttachUiCheats();
         var _loc6_:int = 0;
         var _loc7_:int = int(this.mInputActionSpeedControls.length);
         while(_loc6_ < _loc7_)
         {
            InputActionManager.RegisterAction(this.mInputActionSpeedControls[_loc6_]);
            _loc6_++;
         }
         this.InitGamepad();
      }
      
      protected function SetKeyFrame(param1:Object = null) : void
      {
         var _loc2_:Boolean = EcoFootprint.IsFeatureEnabledForCurrentWorld();
         var _loc3_:Boolean = GameContent.HAS_EP05;
         if(GameplayStateData.IsWeatherEnabled())
         {
            if(_loc3_)
            {
               if(_loc2_)
               {
                  gotoAndPlay(FRAME_WEATHER_SEASON_ECO);
               }
               else
               {
                  gotoAndPlay(FRAME_WEATHER_SEASON);
               }
            }
            else if(_loc2_)
            {
               gotoAndPlay(FRAME_WEATHER_ECO);
            }
            else
            {
               gotoAndPlay(FRAME_WEATHER);
            }
         }
         else if(_loc2_)
         {
            gotoAndPlay(FRAME_ECO_FOOTPRINT);
         }
         else
         {
            gotoAndPlay(FRAME_DEFAULT);
         }
      }
      
      override public function Unload() : void
      {
         super.Unload();
         Ticker.Remove(this);
         this.CloseCameraPanel();
         var _loc1_:int = 0;
         var _loc2_:int = int(this.mInputActionSpeedControls.length);
         while(_loc1_ < _loc2_)
         {
            InputActionManager.UnregisterAction(this.mInputActionSpeedControls[_loc1_]);
            _loc1_++;
         }
         if(SystemUtils.UsingConsoleInputMode)
         {
            InputActionManager.AutounregisterActions([this.mInputActionIncreaseGameSpeed,this.mInputActionDecreaseGameSpeed,this.mInputActionIncreaseGameSpeedFreeCam,this.mInputActionDecreaseGameSpeedFreeCam]);
         }
      }
      
      override public function HandleStageResized(param1:Number, param2:Number) : void
      {
         super.HandleStageResized(param1,param2);
         this.x = 0;
         if(param1 == SimInfoTrayTunables.MIN_STAGE_WIDTH)
         {
            this.x += SimInfoTrayTunables.TIME_CONTROLS_OFFSET_ON_MIN_STAGE_WIDTH;
         }
      }
      
      public function CloseCameraPanel() : void
      {
         this.btnCameraOptions.Selected = false;
         this.btnCameraOptions.AudioExt.ElementName = "CameraOptions";
         this.mcCameraPanel.visible = false;
         RemoveMessageListener("WorldPickDownEvent",this.HandleWorldPickDownEvent);
         InputActionManager.UnregisterAction(this.mInputActionCloseCameraPanel);
         stage.removeEventListener(MouseEvent.CLICK,this.OnStageMouseClick);
      }
      
      public function IncreaseGameSpeed() : void
      {
         var _loc2_:int = 0;
         if(SystemUtils.UsingController && !this.mbGamepadTimeControlsEnabled)
         {
            return;
         }
         var _loc1_:int = Time.mClockSpeed;
         if(_loc1_ >= 0 && _loc1_ < 3)
         {
            _loc2_ = _loc1_ + 1;
            if(!this.mTimeButtonArray[_loc2_].enabled)
            {
               return;
            }
            CommunicationManager.CallGameService("PostServerCommand",{
               "command":"clock.setspeed_internal",
               "commandArgs":[_loc2_]
            });
         }
      }
      
      public function DecreaseGameSpeed() : void
      {
         if(SystemUtils.UsingController && !this.mbGamepadTimeControlsEnabled)
         {
            return;
         }
         var _loc1_:int = Time.mClockSpeed;
         if(_loc1_ == 1)
         {
            this.OnPauseClick(null);
         }
         else if(_loc1_ > 1 && _loc1_ <= 3)
         {
            CommunicationManager.CallGameService("PostServerCommand",{
               "command":"clock.setspeed_internal",
               "commandArgs":[int(_loc1_ - 1)]
            });
         }
      }
      
      protected function HandleWorldPickDownEvent(param1:Object) : void
      {
         this.CloseCameraPanel();
      }
      
      protected function HandleToggleVideoRecord(param1:Object = null) : void
      {
         var _loc2_:Boolean = CommunicationManager.CallUIService("IsVideoRecording") as Boolean;
         if(_loc2_)
         {
            this.btnCameraOptions.EnableStatePrefix("recording");
         }
         else
         {
            this.btnCameraOptions.DisableStatePrefix("recording");
         }
      }
      
      protected function HandleUpdateGameClock(param1:GameClockTime) : void
      {
         if(param1.clockSpeed < this.mTimeButtonArray.length)
         {
            this.mTimeButtonGroup.SetSelectionAs(this.mTimeButtonArray[param1.clockSpeed]);
         }
         this.UpdateTimeText(Time.GetGameTime());
         if(param1.clockSpeed == GlobalTunables.GAME_SPEED_PAUSE)
         {
            this.txtTimeSpeedName.visible = true;
         }
         else
         {
            this.txtTimeSpeedName.visible = false;
         }
         this.OnSuperSpeedEnabled(param1.superSpeed);
         this.UpdateAudioEvents(param1.clockSpeed);
      }
      
      protected function UpdateTimeText(param1:TimeSpan) : void
      {
         var _loc5_:uint = 0;
         if(!param1)
         {
            return;
         }
         var _loc2_:uint = param1.Days % 7;
         if(_loc2_ == 0)
         {
            _loc2_ = 7;
         }
         var _loc3_:TimeSpan = new TimeSpan(0,0,param1.Minutes,param1.Hours,_loc2_);
         if(this.mCurrentDisplayedTimeMilliseconds > 0)
         {
            _loc5_ = _loc3_.ConvertToMilliseconds();
            if(_loc5_ < this.mCurrentDisplayedTimeMilliseconds && this.mCurrentDisplayedTimeMilliseconds - _loc5_ <= TIME_TICK_BACKWARDS_THRESHOLD)
            {
               return;
            }
            this.mCurrentDisplayedTimeMilliseconds = _loc5_;
         }
         else
         {
            this.mCurrentDisplayedTimeMilliseconds = _loc3_.ConvertToMilliseconds();
         }
         var _loc4_:LocKey = Keys.TIME_CONTROLS_CURRENT_DAY_AND_TIME;
         this.txtGameTime.htmlText = _loc4_.toString({
            "token_type":"TimeSpan",
            "token_data":_loc3_
         });
         if(this.mcBlurEffect.visible)
         {
            this.SetBlurPosition();
         }
      }
      
      protected function SetBlurPosition() : void
      {
         var _loc4_:Number = NaN;
         var _loc5_:Rectangle = null;
         var _loc1_:MovieClip = this.mcBlurEffect;
         var _loc2_:TextField = this.txtGameTime;
         // Must stay :int, not :*. FFDec compiles an untyped counter with
         // coerce_a + declocal (a Number decrement), where EA's original uses
         // decrement_i. getCharBoundaries() then takes a Number index, returns
         // null, and the unchecked _loc5_.x below faults natively inside GFx.
         var _loc3_:int = int(_loc2_.text.length - 1);
         while(_loc3_ >= 0)
         {
            _loc4_ = _loc2_.text.charCodeAt(_loc3_);
            if(_loc4_ >= 48 && _loc4_ <= 57)
            {
               _loc5_ = _loc2_.getCharBoundaries(_loc3_);
               _loc1_.x = _loc2_.x + _loc5_.x + TimeControlsTunables.BLUR_EFFECT_OFFSET_X;
               _loc1_.y = _loc2_.y + _loc5_.y + TimeControlsTunables.BLUR_EFFECT_OFFSET_Y;
               return;
            }
            _loc3_--;
         }
      }
      
      protected function Update(param1:TickerEvent) : void
      {
         if(Time.AddToGameTime(param1.deltaSimTimeUsingGameSpeed,TimeSpan.SECONDS))
         {
            this.UpdateTimeText(Time.GetGameTime());
         }
      }
      
      protected function RefreshGameClock() : void
      {
         var _loc1_:int = Time.mClockSpeed;
         if(_loc1_ < this.mTimeButtonArray.length)
         {
            this.mTimeButtonGroup.SetSelectionAs(this.mTimeButtonArray[_loc1_]);
         }
         if(_loc1_ == GlobalTunables.GAME_SPEED_PAUSE)
         {
            this.txtTimeSpeedName.visible = true;
         }
         else
         {
            this.txtTimeSpeedName.visible = false;
         }
         this.OnSuperSpeedEnabled(Time.mSuperSpeed);
      }
      
      protected function OnPauseClick(param1:PushButtonEvent = null) : void
      {
         if(param1 == null)
         {
            this.DispatchGameSpeedKeyChangeEvents(0);
         }
         CommunicationManager.CallGameService("PostServerCommand",{
            "command":"clock.toggle_pause_unpause",
            "commandArgs":[]
         });
         this.txtTimeSpeedName.visible = this.btnPause.Selected;
      }
      
      protected function OnSpeedOneClick(param1:PushButtonEvent = null) : void
      {
         if(param1 == null)
         {
            this.DispatchGameSpeedKeyChangeEvents(1);
         }
         CommunicationManager.CallGameService("PostServerCommand",{
            "command":"clock.setspeed",
            "commandArgs":["one"]
         });
      }
      
      protected function OnSpeedTwoClick(param1:PushButtonEvent = null) : void
      {
         if(param1 == null)
         {
            this.DispatchGameSpeedKeyChangeEvents(2);
         }
         CommunicationManager.CallGameService("PostServerCommand",{
            "command":"clock.setspeed",
            "commandArgs":["two"]
         });
      }
      
      protected function OnSpeedThreeClick(param1:PushButtonEvent = null) : void
      {
         if(!this.mTimeButtonArray[3].enabled)
         {
            return;
         }
         if(param1 == null)
         {
            this.DispatchGameSpeedKeyChangeEvents(3);
         }
         CommunicationManager.CallGameService("PostServerCommand",{
            "command":"clock.setspeed",
            "commandArgs":["three"]
         });
      }
      
      protected function DispatchGameSpeedKeyChangeEvents(param1:int) : void
      {
         var _loc3_:String = null;
         var _loc2_:int = Time.mClockSpeed;
         switch(param1)
         {
            case 0:
               _loc3_ = "GameSpeedPause";
               break;
            case 1:
               if(param1 > _loc2_)
               {
                  _loc3_ = "GameSpeedOne_SpeedUp";
               }
               else if(param1 < _loc2_)
               {
                  _loc3_ = "GameSpeedOne_SlowDown";
               }
               break;
            case 2:
               if(param1 > _loc2_)
               {
                  _loc3_ = "GameSpeedTwo_SpeedUp";
               }
               else if(param1 < _loc2_)
               {
                  _loc3_ = "GameSpeedTwo_SlowDown";
               }
               break;
            case 3:
               _loc3_ = "GameSpeedThree";
         }
         if(_loc3_)
         {
            EventManager.DispatchInteractionEvent(Audio.CUSTOM,"GameplayKeyHandler",_loc3_,"HotkeyPress",null);
         }
      }
      
      protected function OnCameraOptionsClick(param1:PushButtonEvent) : void
      {
         var _loc2_:Boolean = !this.btnCameraOptions.Selected;
         if(_loc2_)
         {
            this.btnCameraOptions.Selected = true;
            this.btnCameraOptions.AudioExt.ElementName = "CameraOptionsOff";
            this.mcCameraPanel.visible = true;
            this.mcCameraPanel.gotoAndPlay(1);
            AddMessageListener("WorldPickDownEvent",this.HandleWorldPickDownEvent);
            InputActionManager.RegisterAction(this.mInputActionCloseCameraPanel);
            stage.addEventListener(MouseEvent.CLICK,this.OnStageMouseClick,false,0,true);
         }
         else
         {
            this.CloseCameraPanel();
         }
      }
      
      protected function OnStageMouseClick(param1:MouseEvent) : void
      {
         if(param1.target == this.btnCameraOptions || param1.target == this.mcCameraPanel)
         {
            return;
         }
         this.CloseCameraPanel();
      }
      
      protected function UpdateAudioEvents(param1:int) : void
      {
         switch(param1)
         {
            case GlobalTunables.GAME_SPEED_PAUSE:
               this.btnSpeedOne.AudioExt.Context = Audio.GAMESPEED_SPEEDUP;
               this.btnSpeedTwo.AudioExt.Context = Audio.GAMESPEED_SPEEDUP;
               this.btnSpeedThree.AudioExt.Context = Audio.GAMESPEED_SPEEDUP;
               break;
            case GlobalTunables.GAME_SPEED_ONE:
               this.btnSpeedOne.AudioExt.Context = null;
               this.btnSpeedTwo.AudioExt.Context = Audio.GAMESPEED_SPEEDUP;
               this.btnSpeedThree.AudioExt.Context = Audio.GAMESPEED_SPEEDUP;
               break;
            case GlobalTunables.GAME_SPEED_TWO:
               this.btnSpeedOne.AudioExt.Context = Audio.GAMESPEED_SLOWDOWN;
               this.btnSpeedTwo.AudioExt.Context = null;
               this.btnSpeedThree.AudioExt.Context = Audio.GAMESPEED_SPEEDUP;
               break;
            case GlobalTunables.GAME_SPEED_THREE:
               this.btnSpeedOne.AudioExt.Context = Audio.GAMESPEED_SLOWDOWN;
               this.btnSpeedTwo.AudioExt.Context = Audio.GAMESPEED_SLOWDOWN;
               this.btnSpeedThree.AudioExt.Context = null;
               break;
            default:
               this.btnSpeedOne.AudioExt.Context = null;
               this.btnSpeedTwo.AudioExt.Context = null;
               this.btnSpeedThree.AudioExt.Context = null;
         }
      }
      
      protected function OnSuperSpeedEnabled(param1:Boolean) : void
      {
         var _loc2_:MovieClip = null;
         if(this.mbSuperSpeedEnabled != param1)
         {
            _loc2_ = this.mcBlurEffect;
            if(param1)
            {
               this.SetBlurPosition();
               _loc2_.gotoAndPlay("start");
               _loc2_.visible = true;
            }
            else
            {
               _loc2_.gotoAndPlay("stop");
            }
            this.mbSuperSpeedEnabled = param1;
         }
      }
      
      protected function HandleCanChangeGameSpeed() : Boolean
      {
         return this.mbGamepadTimeControlsEnabled && CommunicationManager.CallUIService("IsNotInFreeCam") == true;
      }
      
      protected function EnableGamepadTimeControls(param1:Object = null) : void
      {
         this.mbGamepadTimeControlsEnabled = true;
         InputModeVisibilityExtension.SetVisible(this.mLegendIconSlow,true);
         InputModeVisibilityExtension.SetVisible(this.mLegendIconFast,true);
      }
      
      protected function DisableGamepadTimeControls(param1:Object = null) : void
      {
         this.mbGamepadTimeControlsEnabled = false;
         InputModeVisibilityExtension.SetVisible(this.mLegendIconSlow,false);
         InputModeVisibilityExtension.SetVisible(this.mLegendIconFast,false);
      }
      
      protected function InitGamepad() : void
      {
         if(!SystemUtils.UsingConsoleInputMode)
         {
            return;
         }
         this.btnCameraOptions.visible = false;
         this.mcDividingLine.visible = false;
         this.btnPause.x += TimeControlsTunables.CONTROLLER_BUTTON_X_OFFSET;
         this.btnSpeedOne.x += TimeControlsTunables.CONTROLLER_BUTTON_X_OFFSET;
         this.btnSpeedTwo.x += TimeControlsTunables.CONTROLLER_BUTTON_X_OFFSET;
         this.btnSpeedThree.x += TimeControlsTunables.CONTROLLER_BUTTON_X_OFFSET;
         this.mLegendIconSlow = new LegendIcon();
         this.mLegendIconSlow.ActionCode = ActionCodes.TRIGGER_LEFT;
         this.mcGameSpeedSlow.addChild(this.mLegendIconSlow);
         this.mLegendIconFast = new LegendIcon();
         this.mLegendIconFast.ActionCode = ActionCodes.TRIGGER_RIGHT;
         this.mcGameSpeedFast.addChild(this.mLegendIconFast);
         InputModeVisibilityExtension.ShowForController(this.mLegendIconSlow);
         InputModeVisibilityExtension.ShowForController(this.mLegendIconFast);
         InputModeVisibilityExtension.HideForDialog(this.mLegendIconFast,true);
         InputModeVisibilityExtension.HideForDialog(this.mLegendIconSlow,true);
         InputModeVisibilityExtension.HideForShowControlsOverlayOption(this.mLegendIconFast);
         InputModeVisibilityExtension.HideForShowControlsOverlayOption(this.mLegendIconSlow);
         CommunicationManager.AddMessageListener(InputActionManager.EVENT_REGISTERED_ACTIONS_CHANGED,this.HandleRefreshLegendIcons,this);
         CommunicationManager.AddMessageListener("SetModalVisible",this.HandleRefreshLegendIcons,this);
         this.mInputActionIncreaseGameSpeed = InputAction.WhenTriggered(InputTrigger.FromActionCode(ActionCodes.TRIGGER_RIGHT)).DispatchUIMessage("IncreaseGameSpeed").SetValidCheckUIService("CanChangeGameSpeed").SetValidQuickLegendCheck(function():Boolean
         {
            return false;
         }).SetLegendKey(KeysConsole.LIVE_INCREASE_SPEED).RestrictToGameStates(GameStates.PLAY);
         this.mInputActionDecreaseGameSpeed = InputAction.WhenTriggered(InputTrigger.FromActionCode(ActionCodes.TRIGGER_LEFT)).DispatchUIMessage("DecreaseGameSpeed").SetValidCheckUIService("CanChangeGameSpeed").SetValidQuickLegendCheck(function():Boolean
         {
            return false;
         }).SetLegendKey(KeysConsole.LIVE_DECREASE_SPEED).RestrictToGameStates(GameStates.PLAY);
         this.mInputActionIncreaseGameSpeedFreeCam = InputAction.WhenTriggered(InputTrigger.FromActionCode(ActionCodes.TAB_RIGHT)).DispatchUIMessage("IncreaseGameSpeed").SetValidCheckUIService("IsNotInFreeCam",null,false).SetValidQuickLegendCheck(function():Boolean
         {
            return false;
         }).SetLegendKey(KeysConsole.LIVE_INCREASE_SPEED).RestrictToGameStates(GameStates.PLAY);
         this.mInputActionDecreaseGameSpeedFreeCam = InputAction.WhenTriggered(InputTrigger.FromActionCode(ActionCodes.TAB_LEFT)).DispatchUIMessage("DecreaseGameSpeed").SetValidCheckUIService("IsNotInFreeCam",null,false).SetValidQuickLegendCheck(function():Boolean
         {
            return false;
         }).SetLegendKey(KeysConsole.LIVE_DECREASE_SPEED).RestrictToGameStates(GameStates.PLAY);
         InputActionManager.AutoregisterActions([this.mInputActionIncreaseGameSpeed,this.mInputActionDecreaseGameSpeed,this.mInputActionIncreaseGameSpeedFreeCam,this.mInputActionDecreaseGameSpeedFreeCam]);
      }
      
      protected function HandleRefreshLegendIcons(param1:Object) : void
      {
         InputModeVisibilityExtension.SetVisible(this.mLegendIconSlow,InputActionManager.CanInputActionTrigger(this.mInputActionDecreaseGameSpeed,true));
         InputModeVisibilityExtension.SetVisible(this.mLegendIconFast,InputActionManager.CanInputActionTrigger(this.mInputActionIncreaseGameSpeed,true));
      }

      public function A11yAttachUiCheats() : void
      {
         var _loc1_:Class = null;
         var _loc2_:Object = null;
         try
         {
            // UI Cheats Extension's own TimeControlsMain edit is exactly:
            // txtGameTime.mouseEnabled = true (which our clock announcer
            // already needs and does) + attaching its GenericCheatsExtension
            // with cheatType "time". Replicate the attach so BOTH mods work
            // when this movie wins the load order. The class lives in UI
            // Cheats' ClassLibraryOlympus, so resolve it BY NAME at runtime:
            // a compile-time import would be an unresolvable reference
            // without UI Cheats installed, and the AVM faults on those at
            // method VERIFY time, before any try/catch runs (the CAS crash
            // lesson). getDefinitionByName just throws catchably instead,
            // which IS the fallback: no UI Cheats, no extension, no error.
            _loc1_ = getDefinitionByName("olympus.extensions.cheats.GenericCheatsExtension") as Class;
            if(_loc1_ == null)
            {
               return;
            }
            _loc2_ = GetExtension(_loc1_);
            if(_loc2_ != null)
            {
               _loc2_["cheatType"] = "time";
            }
         }
         catch(e:Error)
         {
         }
      }

      public function A11yInButton(param1:DisplayObject) : Boolean
      {
         var _loc2_:DisplayObject = param1;
         var _loc3_:int = 0;
         while(_loc2_ != null && _loc2_ != this && _loc3_ < 12)
         {
            if(_loc2_ == this.btnPause || _loc2_ == this.btnSpeedOne || _loc2_ == this.btnSpeedTwo || _loc2_ == this.btnSpeedThree || _loc2_ == this.btnCameraOptions || _loc2_ == this.mcCameraPanel)
            {
               return true;
            }
            _loc2_ = _loc2_.parent;
            _loc3_++;
         }
         return false;
      }

      public function A11yOnTimeOver(param1:MouseEvent) : void
      {
         var _loc2_:DisplayObject = null;
         var _loc3_:String = null;
         var _loc4_:String = null;
         try
         {
            _loc2_ = param1.target as DisplayObject;
            if(_loc2_ == null)
            {
               return;
            }
            if(this.A11yInButton(_loc2_))
            {
               // Crossing onto a speed/camera button: its own announce takes
               // over; re-entering the clock area afterwards re-reads.
               this.mA11yTimeHovered = false;
               return;
            }
            if(this.mA11yTimeHovered)
            {
               return;
            }
            this.mA11yTimeHovered = true;
            _loc3_ = "";
            try
            {
               _loc3_ = this.txtGameTime.text;
            }
            catch(e1:Error)
            {
            }
            try
            {
               if(this.txtTimeSpeedName.visible && this.txtTimeSpeedName.text.length > 0)
               {
                  _loc3_ += ". " + this.txtTimeSpeedName.text;
               }
            }
            catch(e2:Error)
            {
            }
            if(_loc3_ == null || _loc3_.length == 0)
            {
               return;
            }
            _loc4_ = encodeURIComponent(_loc3_);
            _loc4_ = _loc4_.split("'").join("%27");
            _loc4_ = _loc4_.split("(").join("%28");
            _loc4_ = _loc4_.split(")").join("%29");
            _loc4_ = _loc4_.split("!").join("%21");
            CommunicationManager.PostServerCommand("a11y.timewidget_enc",_loc4_);
         }
         catch(e:Error)
         {
         }
      }

      public function A11yOnTimeOut(param1:MouseEvent) : void
      {
         this.mA11yTimeHovered = false;
      }
      
      internal function frame8() : *
      {
         stop();
      }
      
      internal function frame21() : *
      {
         stop();
      }
      
      internal function frame32() : *
      {
         stop();
      }
      
      internal function frame43() : *
      {
         stop();
      }
      
      internal function frame54() : *
      {
         stop();
      }
      
      internal function frame65() : *
      {
         stop();
      }
   }
}

