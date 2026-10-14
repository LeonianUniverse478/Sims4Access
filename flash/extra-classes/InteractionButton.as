package widgets.Gameplay.InteractionQueue.controls
{
   import flash.display.MovieClip;
   import flash.events.Event;
   import flash.events.MouseEvent;
   import gamedata.Gameplay.shared.GameplayStateData;
   import gamedata.Gameplay.shared.Interaction;
   import gamedata.Gameplay.shared.MoodUpdate;
   import olympus.audio.Audio;
   import olympus.controls.IconComponent;
   import olympus.events.PushButtonEvent;
   import olympus.events.TweenEvent;
   import olympus.extensions.Selectability;
   import olympus.gui.buttons.Button;
   import olympus.io.CommunicationManager;
   import olympus.localization.KeysConsole;
   import olympus.localization.KeysGP;
   import olympus.localization.LocKey;
   import olympus.motion.Tween;
   import olympus.objects.IconInfo;
   import olympus.utils.ImageUtils;
   import widgets.Gameplay.InteractionQueue.constants.InteractionQueueTunables;
   import widgets.shared.controls.ToastNotification.ToastNotification;
   
   public class InteractionButton extends Button
   {
      
      public static const REMOVE_SEQUENCE_COMPLETE:String = "removeSequenceComplete";
      
      public static const CANCEL_REQUESTED:String = "cancelRequested";
      
      protected static const INTERACTION_PREFIX_MAP:Object = {
         "none":[""],
         "selected":["selected_",""],
         "pending":["pending_",""],
         "running":["running_",""],
         "pending_selected":["selected_",""],
         "running_selected":["selected_",""],
         "pending_running_selected":["selected_",""]
      };
      
      public var mcIconContainer:MovieClip;
      
      public var mcCancel:MovieClip;
      
      public var mcBackground:MovieClip;
      
      public var mMoveTween:Tween;
      
      public var mScaleTween:Tween;
      
      public var mMixerInteractionButton:InteractionButton;
      
      public var mInteraction:Interaction;
      
      protected var mcIcon:IconComponent;
      
      public function InteractionButton()
      {
         super();
         mAudioExtension.ElementName = "InteractionButton";
         PrefixMap = INTERACTION_PREFIX_MAP;
      }
      
      override public function set y(param1:Number) : void
      {
         super.y = param1;
         if(this.mMixerInteractionButton)
         {
            this.mMixerInteractionButton.y = param1 + InteractionQueueTunables.MIXER_BUTTON_Y_OFFSET;
         }
      }
      
      public function Reset() : void
      {
      }
      
      public function SetSupporting(param1:Interaction, param2:Boolean = true) : void
      {
         var _loc3_:Interaction = this.mInteraction;
         var _loc4_:InteractionButton = this.mMixerInteractionButton;
         var _loc5_:Boolean = Boolean(_loc3_) && _loc3_.visual_type == Interaction.VISUAL_TYPE_PARENT && _loc3_.queue_ui_state == Interaction.IQ_UI_STATE_RUNNING;
         var _loc6_:Boolean = _loc3_ && param1 && _loc3_.interaction_id == param1.interaction_id && param1.visual_type == Interaction.VISUAL_TYPE_MIXER;
         if(!_loc4_ && (_loc5_ || _loc6_))
         {
            _loc4_ = new MixerInteractionButton();
            if(parent)
            {
               parent.addChild(_loc4_);
            }
            _loc4_.x = InteractionQueueTunables.RUNNING_BUTTON_X + InteractionQueueTunables.MIXER_BUTTON_X_OFFSET;
            _loc4_.y = this.y + InteractionQueueTunables.MIXER_BUTTON_Y_OFFSET;
            if(param2)
            {
               Tween.AnimateClip(InteractionQueueTunables.INTERACTION_CONTAINER_BUTTON_ANIMATION.duration,InteractionQueueTunables.INTERACTION_CONTAINER_BUTTON_ADD_ANIMATION,_loc4_);
            }
         }
         if(_loc4_)
         {
            _loc4_.Draw(param1);
            if(param1 == null)
            {
               Tween.StopAllTweens(_loc4_,true,true);
               _loc4_.visible = false;
            }
            else
            {
               _loc4_.visible = true;
            }
         }
         this.mMixerInteractionButton = _loc4_;
      }
      
      public function get InteractionId() : String
      {
         if(this.mInteraction)
         {
            return this.mInteraction.interaction_id;
         }
         return null;
      }
      
      public function get SupportingInteractionId() : String
      {
         if(this.mMixerInteractionButton)
         {
            return this.mMixerInteractionButton.InteractionId;
         }
         return null;
      }
      
      override public function Draw(param1:Object, param2:Object = null) : void
      {
         var _loc6_:Boolean = false;
         var _loc7_:IconInfo = null;
         var _loc8_:String = null;
         var _loc9_:String = null;
         super.Draw(param1,param2);
         var _loc3_:Interaction = param1 as Interaction;
         var _loc4_:Selectability = GetExtension(Selectability) as Selectability;
         this.mInteraction = _loc3_;
         this.mcIcon = this.mcIconContainer.mcIcon;
         if(!_loc3_)
         {
            enabled = true;
            _loc4_.Selected = false;
            this.mcIcon.LoadImage(null);
            mTooltipExtension.Clear();
            return;
         }
         enabled = !_loc3_.canceled;
         _loc4_.Selected = _loc3_.canceled;
         if(_loc3_.queue_ui_state == Interaction.IQ_UI_STATE_TRANSITIONING)
         {
            SetStatePrefix("pending");
         }
         else if(_loc3_.queue_ui_state == Interaction.IQ_UI_STATE_RUNNING)
         {
            SetStatePrefix("running");
            this.A11yAnnounceRunning(_loc3_);
         }
         if(!_loc3_.cancelable)
         {
            removeEventListener(MouseEvent.ROLL_OVER,OnMouseRollOver);
            removeEventListener(MouseEvent.ROLL_OUT,OnMouseRollOut);
            removeEventListener(PushButtonEvent.CLICK,this.OnButtonClick);
            addEventListener(MouseEvent.ROLL_OVER,this.HandleNonCancelableTooltip,false,0,true);
            addEventListener(MouseEvent.ROLL_OUT,this.HandleNonCancelableTooltip,false,0,true);
         }
         else
         {
            addEventListener(MouseEvent.ROLL_OVER,OnMouseRollOver,false,0,true);
            addEventListener(MouseEvent.ROLL_OUT,OnMouseRollOut,false,0,true);
            addEventListener(PushButtonEvent.CLICK,this.OnButtonClick,false,0,true);
            removeEventListener(MouseEvent.ROLL_OVER,this.HandleNonCancelableTooltip);
            removeEventListener(MouseEvent.ROLL_OUT,this.HandleNonCancelableTooltip);
         }
         var _loc5_:MoodUpdate = GameplayStateData.CurrentMood;
         if(_loc3_.mood_list.indexOf(_loc5_.mood_key) != -1)
         {
            this.mcBackground.gotoAndStop(_loc5_.MoodName);
         }
         else
         {
            this.mcBackground.gotoAndStop("default");
         }
         if(!_loc3_.cancelable)
         {
            this.mcCancel.visible = false;
         }
         else
         {
            this.mcCancel.visible = true;
         }
         if(_loc3_.visual_type == Interaction.VISUAL_TYPE_MIXER && !(this is MixerInteractionButton))
         {
            _loc7_ = _loc3_.super_icon_info;
            if(_loc7_)
            {
               _loc8_ = _loc7_.name.toString();
               _loc9_ = _loc3_.icon_info ? _loc3_.icon_info.GetName() : "";
               if(_loc9_)
               {
                  mTooltipExtension.SetText(KeysGP.SUPER_MIXER_TOOLTIP,_loc8_,_loc9_);
               }
               else
               {
                  mTooltipExtension.Text = _loc8_;
               }
               _loc6_ = ImageUtils.LoadFromIconInfo(this.mcIcon,_loc7_,ImageUtils.THUMBNAIL_SIZE_MEDIUM,true);
               if(!_loc6_)
               {
                  this.mcIcon.LoadImage(_loc7_.icon.instance);
               }
               return;
            }
         }
         if(_loc3_.icon_info)
         {
            mTooltipExtension.SetText(_loc3_.icon_info.name);
            _loc6_ = ImageUtils.LoadFromIconInfo(this.mcIcon,_loc3_.icon_info,ImageUtils.THUMBNAIL_SIZE_MEDIUM,true);
            if(!_loc6_)
            {
               this.mcIcon.LoadImage(_loc3_.icon_info.icon.instance);
            }
         }
      }
      
      protected static var sA11yLastRun:String = "";

      public function A11yAnnounceRunning(param1:Interaction) : void
      {
         var _loc2_:String = null;
         var _loc3_:String = null;
         try
         {
            if(param1.icon_info != null)
            {
               _loc2_ = param1.icon_info.GetName();
            }
            if((_loc2_ == null || _loc2_.length == 0) && param1.super_icon_info != null)
            {
               _loc2_ = param1.super_icon_info.name.toString();
            }
            if(_loc2_ == null || _loc2_.length == 0)
            {
               return;
            }
            if(_loc2_ == sA11yLastRun)
            {
               return;
            }
            sA11yLastRun = _loc2_;
            _loc3_ = encodeURIComponent(_loc2_);
            _loc3_ = _loc3_.split("'").join("%27");
            _loc3_ = _loc3_.split("(").join("%28");
            _loc3_ = _loc3_.split(")").join("%29");
            _loc3_ = _loc3_.split("!").join("%21");
            CommunicationManager.PostServerCommand("a11y.simaction_enc",_loc3_);
         }
         catch(e:Error)
         {
         }
      }

      public function TriggerRemoval() : void
      {
         this.mScaleTween = Tween.CreateFromParams(InteractionQueueTunables.INTERACTION_CONTAINER_BUTTON_REMOVE_ANIMATION,this);
         this.mScaleTween.addEventListener(TweenEvent.TWEEN_COMPLETE,this.OnRemoveTweenComplete,false,0,true);
         this.mScaleTween.Start();
      }
      
      override protected function ConfigUI() : void
      {
         super.ConfigUI();
         this.mcIcon = this.mcIconContainer.mcIcon;
      }
      
      override protected function OnRemovedFromStage(param1:Event) : void
      {
         super.OnRemovedFromStage(param1);
         var _loc2_:InteractionButton = this.mMixerInteractionButton;
         if(Boolean(_loc2_) && Boolean(_loc2_.parent))
         {
            _loc2_.parent.removeChild(_loc2_);
         }
      }
      
      protected function OnButtonClick(param1:PushButtonEvent) : void
      {
         this.RequestCancel();
      }
      
      public function RequestCancel() : void
      {
         dispatchEvent(new Event(InteractionButton.CANCEL_REQUESTED));
         if(!this.mInteraction)
         {
            return;
         }
         if(!this.mInteraction.cancelable)
         {
            return;
         }
         Selected = true;
         enabled = false;
         mTooltipExtension.Clear();
         mAudioExtension.Dispatch(Audio.CUSTOM,Audio.INTERACTION_CANCELLED);
         CommunicationManager.CallGameService("PostServerCommand",{
            "command":"interactions.cancel_si",
            "commandArgs":[this.mInteraction.interaction_id,this.mInteraction.context_handle]
         });
         CommunicationManager.SendUIMessage("ToastNotify",{
            "type":ToastNotification.TYPE_CLOBBER,
            "label":LocKey(KeysConsole.LIVE_ACTION_CANCELED).toString(),
            "isControllerFeedback":true
         });
      }
      
      protected function HandleNonCancelableTooltip(param1:MouseEvent) : void
      {
         mTooltipExtension.SendTooltipEvent(param1);
      }
      
      protected function OnRemoveTweenComplete(param1:TweenEvent) : void
      {
         dispatchEvent(new Event(InteractionButton.REMOVE_SEQUENCE_COMPLETE));
      }
   }
}

