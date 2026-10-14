package widgets.Notifications
{
   import flash.display.MovieClip;
   import flash.events.Event;
   import flash.events.MouseEvent;
   import flash.events.TimerEvent;
   import flash.utils.Timer;
   import gamedata.Gameplay.Persistence.GameSaveLockUnlock;
   import gamedata.shared.NotificationStaticData;
   import gamedata.shared.UiDialogNotification;
   import olympus.audio.Audio;
   import olympus.constants.GameStates;
   import olympus.core.UISettings;
   import olympus.core.widget.WidgetBase;
   import olympus.extensions.Selectability;
   import olympus.gamepad.EnterParams;
   import olympus.gamepad.NavManager;
   import olympus.input.IInputFocusable;
   import olympus.input.adapters.DynamicOmnidirectionalAdapter;
   import olympus.io.CommunicationManager;
   import olympus.io.EventManager;
   import olympus.motion.Tween;
   import olympus.utils.SystemUtils;
   import widgets.shared.controls.Notifications.NotificationView;
   import widgets.shared.controls.Notifications.NotificationsTunables;
   import widgets.shared.utils.SharedExchangeUtils;
   
   public class NotificationsMain extends WidgetBase
   {
      
      public var mcNotificationView:NotificationView;
      
      public var mcQueuedEffect:MovieClip;
      
      protected var mNotificationStaticData:NotificationStaticData;
      
      protected var mNotificationDataFeed:NotificationDataFeed;
      
      protected var mHideTimer:Timer;
      
      protected var mCollapseTimer:Timer;
      
      protected var mbUserInteracting:Boolean = false;
      
      protected var mbExpanded:Boolean = false;
      
      protected var mbPinned:Boolean = false;
      
      protected var mbForceExpanded:Boolean = false;
      
      protected var mGameState:uint = 2530218128;
      
      protected var mWallOpen:Boolean = false;
      
      protected var mQueuedEffectOffset:Number = 0;
      
      protected var mQueuedEffectBackground:MovieClip;
      
      protected var mSaveLockState:GameSaveLockUnlock;
      
      protected var mMainAdapter:DynamicOmnidirectionalAdapter;
      
      public function NotificationsMain()
      {
         super();
      }
      
      override public function Initialize() : void
      {
         super.Initialize();
         Telemetry.EnableVisibilityTelemetry = false;
         visible = false;
         this.mNotificationDataFeed = new NotificationDataFeed();
         this.mNotificationStaticData = NotificationStaticData.STATIC_DATA;
         var _loc1_:Number = this.mNotificationStaticData.collapse_time;
         this.mCollapseTimer = new Timer(_loc1_);
         this.mCollapseTimer.addEventListener(TimerEvent.TIMER,this.HandleCollapseTimeOut,false,0,true);
         var _loc2_:NotificationView = this.mcNotificationView;
         _loc2_.addEventListener(MouseEvent.ROLL_OVER,this.HandleMouseRollOver,false,0,true);
         _loc2_.addEventListener(MouseEvent.ROLL_OUT,this.HandleMouseRollOut,false,0,true);
         _loc2_.addEventListener(NotificationView.DISMISS_EVENT,this.HandleNotificationDismiss,false,0,true);
         _loc2_.addEventListener(NotificationView.PIN_EVENT,this.HandleNotificationPinned,false,0,true);
         _loc2_.addEventListener(NotificationView.PROMPT_CLICKED,this.HandlePromptClicked,false,0,true);
         AddMessageListener("AddUiDialogNotification",this.HandleAddUiDialogNotification,UiDialogNotification);
         AddMessageListener("RemoveUiDialogNotification",this.HandleRemoveUiDialogNotification);
         AddMessageListener("RemoveMatchingUiDialogNotifications",this.HandleRemoveMatchingUiDialogNotifications);
         AddMessageListener("GameStateChanged",this.HandleGameStateChanged);
         AddMessageListener("ShowCameraControl",this.HandleShowCameraControl);
         AddMessageListener("HideCameraControl",this.HandleHideCameraControl);
         AddMessageListener("UnloadedCameraControl",this.HandleHideCameraControl);
         AddMessageListener("ShowNotificationWall",this.HandleShowNotificationWall);
         AddMessageListener("HideNotificationWall",this.HandleHideNotificationWall);
         AddMessageListener("SetModalVisible",this.HandleSetModalVisible);
         AddMessageListener("TransitionScreenUp",this.HandleTransitionScreenUp);
         AddMessageListener("TransitionScreenHidden",this.HandleTransitionScreenHidden);
         AddMessageListener("GameSaveLockUnlock",this.HandleGameSaveLockUnlock,GameSaveLockUnlock);
         this.mGameState = CommunicationManager.CallGameService("GetGameState") as uint;
         this.mcQueuedEffect.visible = false;
         this.mQueuedEffectOffset = this.mcQueuedEffect.y - this.mcNotificationView.y;
         this.mQueuedEffectBackground = this.mcQueuedEffect.mcAnimationClip.mcBackground;
         this.mbPinned = UISettings.AccountSettings.GetValue(NotificationsTunables.USER_EXPAND_SETTING) as Boolean;
         (_loc2_.btnPin.GetExtension(Selectability) as Selectability).Selected = this.mbPinned;
         if(SystemUtils.UsingConsoleInputMode)
         {
            this.InitGamepad();
         }
      }
      
      override public function Unload() : void
      {
         super.Unload();
      }
      
      override public function Show(param1:Object = null) : void
      {
         super.Show(param1);
         this.mcNotificationView.Draw(param1.data,{
            "IsExpanded":param1.expanded,
            "InWall":false,
            "IsUpdate":param1.IsUpdate
         });
         this.mcNotificationView.SetGameSaveLockState(this.mSaveLockState);
         this.mQueuedEffectBackground.height = this.mcNotificationView.GoalHeight;
      }
      
      override public function Hide(param1:Object = null) : void
      {
         var _loc3_:UiDialogNotification = null;
         super.Hide(param1);
         if(this.mHideTimer)
         {
            this.mHideTimer.removeEventListener(TimerEvent.TIMER,this.HandleHideTimeOut,false);
            this.mHideTimer = null;
         }
         this.mCollapseTimer.reset();
         var _loc2_:Boolean = param1.showNextMessage as Boolean;
         if(_loc2_)
         {
            this.mNotificationDataFeed.RemoveItemAt(0);
         }
         if(this.mNotificationDataFeed.length > 1)
         {
            _loc3_ = this.mNotificationDataFeed.RequestItemAt(1) as UiDialogNotification;
            NotificationView.SetBackgroundFrame(_loc3_,this.mQueuedEffectBackground);
         }
         else
         {
            this.mcQueuedEffect.visible = false;
         }
         if(_loc2_)
         {
            this.ShowNextMessage();
         }
         if(SystemUtils.UsingController)
         {
            NavManager.Instance.TryFocusBack(this.mMainAdapter);
         }
      }
      
      protected function ShowNextMessage() : void
      {
         var _loc1_:UiDialogNotification = null;
         var _loc2_:String = null;
         var _loc3_:Number = NaN;
         var _loc4_:Object = null;
         if(this.mNotificationDataFeed.length > 0)
         {
            _loc1_ = this.mNotificationDataFeed.RequestItemAt(0) as UiDialogNotification;
            _loc2_ = _loc1_.text.toString();
            _loc3_ = Math.max(NotificationStaticData.MINIMUM_WALL_TIME_MILLISECONDS,_loc2_.length * this.mNotificationStaticData.send_to_wall_time_per_char);
            this.mHideTimer = new Timer(_loc3_);
            this.mHideTimer.addEventListener(TimerEvent.TIMER,this.HandleHideTimeOut,false,0,false);
            this.StartHideTimer();
            this.mbForceExpanded = _loc1_.expand_behavior == UiDialogNotification.EXPAND_BEHAVIOR_FORCE;
            this.mbExpanded = this.mbForceExpanded || this.mbPinned || this.mbUserInteracting;
            _loc4_ = {
               "data":_loc1_,
               "expanded":this.mbExpanded,
               "IsUpdate":false
            };
            CommunicationManager.SendUIMessage("ShowNotifications",_loc4_);
         }
         else
         {
            this.mbUserInteracting = false;
         }
      }
      
      protected function StartHideTimer(param1:Boolean = true, param2:Boolean = true) : void
      {
         this.mHideTimer.start();
         if(Boolean(this.mbUserInteracting) || Boolean(param1 && CommunicationManager.CallUIService("IsModalVisible")) || Boolean(param2) && Boolean(CommunicationManager.CallUIService("IsUILoading")))
         {
            this.mHideTimer.stop();
         }
      }
      
      protected function HandleMouseRollOver(param1:MouseEvent) : void
      {
         var _loc2_:Object = null;
         if(!visible)
         {
            return;
         }
         this.mbUserInteracting = true;
         this.mHideTimer.stop();
         this.mCollapseTimer.reset();
         if(!this.mbExpanded)
         {
            this.mbExpanded = true;
            _loc2_ = {
               "data":this.mNotificationDataFeed.RequestItemAt(0),
               "expanded":this.mbExpanded,
               "IsUpdate":true
            };
            CommunicationManager.SendUIMessage("ShowNotifications",_loc2_);
         }
      }
      
      protected function HandleMouseRollOut(param1:MouseEvent) : void
      {
         if(!visible)
         {
            return;
         }
         this.mbUserInteracting = false;
         if(!this.mbPinned && !this.mbForceExpanded)
         {
            this.mCollapseTimer.start();
         }
         else
         {
            this.StartHideTimer();
         }
      }
      
      protected function HandleNotificationDismiss(param1:Event) : void
      {
         CommunicationManager.SendUIMessage("HideNotifications",{"showNextMessage":true});
      }
      
      protected function HandleNotificationPinned(param1:Event) : void
      {
         this.mbPinned = !this.mbPinned;
         UISettings.AccountSettings.SetValue(NotificationsTunables.USER_EXPAND_SETTING,this.mbPinned);
         if(this.mbPinned)
         {
            this.mCollapseTimer.reset();
         }
      }
      
      protected function HandlePromptClicked(param1:Event) : void
      {
         CommunicationManager.SendUIMessage("HideNotifications",{"showNextMessage":true});
      }
      
      protected function HandleHideTimeOut(param1:TimerEvent) : void
      {
         CommunicationManager.SendUIMessage("HideNotifications",{"showNextMessage":true});
      }
      
      protected function HandleCollapseTimeOut(param1:TimerEvent) : void
      {
         this.StartHideTimer();
         this.mCollapseTimer.reset();
         this.mbExpanded = false;
         var _loc2_:Object = {
            "data":this.mNotificationDataFeed.RequestItemAt(0),
            "expanded":this.mbExpanded,
            "IsUpdate":true
         };
         CommunicationManager.SendUIMessage("ShowNotifications",_loc2_);
      }
      
      public function A11yAnnounceNotification(param1:UiDialogNotification) : void
      {
         var _loc2_:String = null;
         var _loc3_:String = null;
         try
         {
            _loc2_ = "";
            if(param1.title != null)
            {
               _loc2_ = param1.title.toString();
            }
            if(param1.text != null)
            {
               if(_loc2_.length > 0)
               {
                  _loc2_ += ". ";
               }
               _loc2_ += param1.text.toString();
            }
            if(_loc2_.length == 0)
            {
               return;
            }
            _loc3_ = encodeURIComponent(_loc2_);
            _loc3_ = _loc3_.split("'").join("%27");
            _loc3_ = _loc3_.split("(").join("%28");
            _loc3_ = _loc3_.split(")").join("%29");
            _loc3_ = _loc3_.split("!").join("%21");
            CommunicationManager.PostServerCommand("a11y.event_enc",_loc3_);
         }
         catch(e:Error)
         {
         }
      }

      protected function HandleAddUiDialogNotification(param1:UiDialogNotification) : void
      {
         var _loc2_:Boolean = param1.criticality == UiDialogNotification.CRITICALITY_URGENT;
         var _loc3_:Boolean = _loc2_ && !this.mbUserInteracting;
         if(this.mWallOpen)
         {
            return;
         }
         if(!SharedExchangeUtils.CanShowSocialFeedNotification(param1))
         {
            return;
         }
         EventManager.DispatchInteractionEvent(Audio.SHOW,"NotificationView","NotificationsMain","NewNotification");
         this.A11yAnnounceNotification(param1);
         if(_loc3_)
         {
            this.mNotificationDataFeed.AddItemToFront(param1);
            CommunicationManager.SendUIMessage("HideNotifications",{"showNextMessage":false});
         }
         else if(_loc2_)
         {
            this.mNotificationDataFeed.AddItemAtIndex(param1,1);
            NotificationView.SetBackgroundFrame(param1,this.mQueuedEffectBackground);
         }
         else
         {
            if(this.mNotificationDataFeed.length == 1)
            {
               NotificationView.SetBackgroundFrame(param1,this.mQueuedEffectBackground);
            }
            this.mNotificationDataFeed.AddItem(param1);
         }
         if(visible || _loc3_ && this.mNotificationDataFeed.length > 1)
         {
            this.mcQueuedEffect.visible = true;
            this.mcQueuedEffect.gotoAndPlay("animate");
         }
         var _loc4_:Boolean = this.mGameState != GameStates.STARTUP;
         if((!visible || _loc3_) && _loc4_)
         {
            this.ShowNextMessage();
         }
      }
      
      protected function HandleRemoveUiDialogNotification(param1:Object) : void
      {
         var _loc2_:int = this.mNotificationDataFeed.GetItemIndexByFieldName("save_uid",param1["save_uid"]);
         if(_loc2_ == 0)
         {
            CommunicationManager.SendUIMessage("HideNotifications",{"showNextMessage":false});
         }
         this.mNotificationDataFeed.RemoveItemAt(_loc2_);
      }
      
      protected function HandleRemoveMatchingUiDialogNotifications(param1:Object) : void
      {
         var _loc2_:Function = param1["predicate"] as Function;
         if(!_loc2_)
         {
            return;
         }
         var _loc3_:int = int(this.mNotificationDataFeed.length - 1);
         while(_loc3_ > 0)
         {
            if(_loc2_(this.mNotificationDataFeed.RequestItemAt(_loc3_)))
            {
               this.mNotificationDataFeed.RemoveItemAt(_loc3_);
            }
            _loc3_--;
         }
         if(this.mNotificationDataFeed.length > 0)
         {
            if(_loc2_(this.mNotificationDataFeed.RequestItemAt(0)))
            {
               this.Hide({"showNextMessage":true});
            }
         }
         if(this.mNotificationDataFeed.length <= 1)
         {
            this.mcQueuedEffect.visible = false;
         }
      }
      
      protected function HandleGameStateChanged(param1:Object) : void
      {
         this.mGameState = param1 as uint;
         var _loc2_:Boolean = this.mGameState != GameStates.STARTUP;
         if(this.mGameState == GameStates.ENTER_MAIN_MENU)
         {
            this.mNotificationDataFeed.RemoveAllItems();
            CommunicationManager.SendUIMessage("HideNotifications",{"showNextMessage":false});
            return;
         }
         if(!visible && _loc2_)
         {
            this.ShowNextMessage();
         }
      }
      
      protected function HandleShowCameraControl(param1:Object) : void
      {
         var _loc2_:Tween = null;
         if(visible && this.mcNotificationView.visible)
         {
            Tween.StopAllTweens(this.mcNotificationView,false,true);
            _loc2_ = Tween.CreateFromParams(NotificationsTunables.CAMERA_CONTROL_MOVE_TWEEN,this.mcNotificationView,{"y":NotificationsTunables.CAMERA_CONTROL_HEIGHT});
            _loc2_.Start();
            Tween.StopAllTweens(this.mcQueuedEffect,false,true);
            _loc2_ = Tween.CreateFromParams(NotificationsTunables.CAMERA_CONTROL_MOVE_TWEEN,this.mcQueuedEffect,{"y":NotificationsTunables.CAMERA_CONTROL_HEIGHT + this.mQueuedEffectOffset});
            _loc2_.Start();
         }
         else
         {
            this.mcNotificationView.y = NotificationsTunables.CAMERA_CONTROL_HEIGHT;
            this.mcQueuedEffect.y = NotificationsTunables.CAMERA_CONTROL_HEIGHT + this.mQueuedEffectOffset;
         }
      }
      
      protected function HandleHideCameraControl(param1:Object) : void
      {
         var _loc2_:Tween = null;
         if(visible && this.mcNotificationView.visible)
         {
            Tween.StopAllTweens(this.mcNotificationView,false,true);
            _loc2_ = Tween.CreateFromParams(NotificationsTunables.CAMERA_CONTROL_MOVE_TWEEN,this.mcNotificationView,{"y":0});
            _loc2_.Start();
            Tween.StopAllTweens(this.mcQueuedEffect,false,true);
            _loc2_ = Tween.CreateFromParams(NotificationsTunables.CAMERA_CONTROL_MOVE_TWEEN,this.mcQueuedEffect,{"y":this.mQueuedEffectOffset});
            _loc2_.Start();
         }
         else
         {
            this.mcNotificationView.y = 0;
            this.mcQueuedEffect.y = this.mQueuedEffectOffset;
         }
      }
      
      protected function HandleShowNotificationWall(param1:Object) : void
      {
         this.mWallOpen = true;
         this.mNotificationDataFeed.RemoveAllItems();
         CommunicationManager.SendUIMessage("HideNotifications",{"showNextMessage":false});
      }
      
      protected function HandleHideNotificationWall(param1:Object) : void
      {
         this.mWallOpen = false;
      }
      
      protected function HandleSetModalVisible(param1:Object) : void
      {
         var _loc2_:Boolean = param1 as Boolean;
         if(!visible)
         {
            return;
         }
         if(_loc2_)
         {
            this.mHideTimer.stop();
         }
         else
         {
            this.StartHideTimer(false,true);
         }
      }
      
      protected function HandleTransitionScreenUp(param1:Object) : void
      {
         var _loc2_:Boolean = param1 as Boolean;
         if(!visible)
         {
            return;
         }
         this.mHideTimer.stop();
      }
      
      protected function HandleTransitionScreenHidden(param1:Object) : void
      {
         var _loc2_:Boolean = param1 as Boolean;
         if(!visible)
         {
            return;
         }
         this.StartHideTimer(true,false);
      }
      
      protected function HandleGameSaveLockUnlock(param1:GameSaveLockUnlock) : void
      {
         this.mSaveLockState = param1;
         if(visible)
         {
            this.mcNotificationView.SetGameSaveLockState(this.mSaveLockState);
         }
      }
      
      protected function InitGamepad() : void
      {
         this.mMainAdapter = new DynamicOmnidirectionalAdapter(this);
         this.mMainAdapter.IncludeObjectsWithTooltips();
         this.mMainAdapter.OnBackCall(NavManager.Instance.FocusBack);
         this.mMainAdapter.EnablePanOnLeave();
      }
      
      override public function Enter(param1:EnterParams = null) : IInputFocusable
      {
         return this.mMainAdapter.Enter(param1);
      }
   }
}

