package widgets.Gameplay.SimInfoHUD.MotivePanel
{
   import flash.display.MovieClip;
   import flash.events.MouseEvent;
   import flash.geom.ColorTransform;
   import flash.text.TextField;
   import flash.utils.Dictionary;
   import flash.utils.getDefinitionByName;
   import gamedata.Gameplay.Buffs.BuffInfo;
   import gamedata.Gameplay.Buffs.definitions.BuffMotiveOverlay;
   import gamedata.Gameplay.SimHub.definitions.CommodityStaticData;
   import gamedata.Gameplay.SimInfoHUD.CommodityProgressUpdate;
   import gamedata.Gameplay.SimInfoHUD.CommodityState;
   import gamedata.Gameplay.shared.GameplayStateData;
   import gamedata.Gameplay.shared.definitions.MoodStaticData;
   import gamedata.TutorialTip.TutorialMode;
   import gamedata.shared.ResourceKey;
   import olympus.controls.GUIComponent;
   import olympus.core.Time;
   import olympus.core.tooltip.Tooltip;
   import olympus.core.widget.Margin;
   import olympus.events.GenericEvent;
   import olympus.events.PushButtonEvent;
   import olympus.events.TweenEvent;
   import olympus.extensions.LoopingAnimExtension;
   import olympus.extensions.TooltipExtension;
   import olympus.extensions.cheats.ProgressBarCheatExtension;
   import olympus.gui.progressbars.ProgressBar;
   import olympus.io.CommunicationManager;
   import olympus.localization.Keys;
   import olympus.localization.KeysGP;
   import olympus.motion.ColorTween;
   import olympus.motion.Tween;
   import olympus.motion.TweenParams;
   import olympus.objects.SimPB;
   import widgets.shared.controls.IconTooltip;
   
   public class CommodityContainer extends GUIComponent
   {
      
      protected static const DELTA_CHANGE_DRAW_THRESHOLD:Number = 2;
      
      public static const UPDATE_MOTIVE_PANEL_WARNING_EVENT:String = "UpdateMotivePanelWarning";
      
      protected static var sFillColorTweens:Dictionary = new Dictionary();
      
      public var mcBar:ProgressBar;
      
      public var btnSolve:MotiveSolveButton;
      
      public var mcBuffIcon:BuffIconComponent;
      
      public var mcArrows:MovieClip;
      
      public var txtTitle:TextField;
      
      public var mcBackground:MovieClip;
      
      public var mcOverlay:GUIComponent;
      
      public var mcStateChangeOverlay:MovieClip;
      
      protected var mCurrentTween:Tween;
      
      protected var mNextTween:Tween;
      
      protected var mActiveArrowTween:Tween;
      
      protected var mPassiveArrowTween:Tween;
      
      protected var mDummyArrowTween:Tween;
      
      protected var mCommodityData:CommodityStaticData;
      
      protected var mChangeRate:Number = 0;
      
      protected var mState:uint = 0;
      
      protected var mCurrentDeltaChange:Number = 0;
      
      protected var mCurrentDeltaMinutes:Number = 0;
      
      protected var mOriginalY:Number;
      
      protected var mOriginalBarY:Number;
      
      protected var mOriginalBtnSolveY:Number;
      
      protected var mOriginalBtnSolveIconY:Number;
      
      protected var mOriginalBuffIconY:Number;
      
      protected var mOriginalBuffIconImageY:Number;
      
      protected var mOriginalTxtTitleY:Number;
      
      protected var mOriginalBackgroundY:Number;
      
      protected var btnTooltip:TooltipExtension;
      
      protected var containerTooltip:TooltipExtension;
      
      protected var barTooltip:TooltipExtension;
      
      protected var mRenderStyle:int = CommodityStaticData.MOTIVE_UI_STYLE_DEFAULT;
      
      protected var mbOverlayActive:Boolean = false;
      
      protected var mbShowBuffIcon:Boolean = true;
      
      protected var mbShowSolveButton:Boolean = true;
      
      protected var mbArrowsUseLongAnimations:Boolean = false;
      
      protected var mBuffsImpactingMotive:Array = [];
      
      protected var mVisibleBuffId:String;
      
      public function CommodityContainer()
      {
         super();
      }
      
      public static function SetColorOnClip(param1:uint, param2:MovieClip, param3:Boolean) : void
      {
         var _loc6_:ColorTween = null;
         var _loc7_:TweenParams = null;
         var _loc4_:ColorTween = sFillColorTweens[param2];
         if(_loc4_)
         {
            _loc4_.Stop();
         }
         var _loc5_:ColorTransform = new ColorTransform();
         if(param1 != 0)
         {
            _loc5_.color = param1;
         }
         if(param3)
         {
            _loc7_ = TweenParams.TweenParam().Duration(400);
            _loc6_ = ColorTween.CreateFromParams(_loc7_,param2,_loc5_);
            _loc6_.Start();
            sFillColorTweens[param2] = _loc6_;
         }
         else
         {
            param2.transform.colorTransform = _loc5_;
         }
      }
      
      override protected function ConfigUI() : void
      {
         super.ConfigUI();
         this.mcArrows.mouseEnabled = false;
         this.mcOverlay.visible = false;
         this.mDummyArrowTween = Tween.CreateFromParams(SimInfoMotivePanelTunables.DUMMY_ARROW_TWEEN_PARAMS,this.mcArrows);
         addEventListener(MouseEvent.ROLL_OVER,this.A11yOnMotiveRollOver,false,0,true);
      }

      public function A11yMotiveText() : String
      {
         var _loc2_:String = null;
         var _loc4_:Number = NaN;
         var _loc5_:Number = NaN;
         var _loc6_:Number = NaN;
         try
         {
            if(this.mCommodityData == null)
            {
               return "";
            }
            _loc2_ = this.mCommodityData.commodity_name.toString();
            if(_loc2_ == null || _loc2_.length == 0)
            {
               return "";
            }
            _loc4_ = this.Value;
            _loc5_ = this.mCommodityData.min_value_tuning;
            _loc6_ = this.mCommodityData.max_value_tuning;
            if(_loc6_ > _loc5_)
            {
               _loc4_ = Math.round((_loc4_ - _loc5_) / (_loc6_ - _loc5_) * 100);
            }
            else
            {
               _loc4_ = Math.round(_loc4_);
            }
            _loc2_ = _loc2_ + ". " + _loc4_.toString() + "%";
            return _loc2_;
         }
         catch(e:Error) { }
         return "";
      }

      public function A11yOnMotiveRollOver(param1:MouseEvent) : void
      {
         var manager:Object = null;
         try
         {
            manager = getDefinitionByName("olympus.core.TooltipManager")["getInstance"]();
            // Keyboard focus announces this whole need with the panel intro.
            // Its synthetic rollover must not independently speak it first.
            if(manager == null || manager["mA11ySyntheticHover"]) { return; }
            manager["A11yAnnounceDisplay"](this,"a11y.widget_enc",false);
         }
         catch(e:Error)
         {
         }
      }
      
      override public function get height() : Number
      {
         return hitArea.height;
      }
      
      public function get CommodityData() : CommodityStaticData
      {
         return this.mCommodityData;
      }
      
      public function get RenderStyle() : int
      {
         return this.mRenderStyle;
      }
      
      public function get IsOverlayActive() : Boolean
      {
         return this.mbOverlayActive;
      }
      
      override public function set visible(param1:Boolean) : void
      {
         super.visible = param1;
         this.mcBar.visible = param1;
         this.btnSolve.visible = param1;
         if(!param1)
         {
            this.mcBuffIcon.visible = param1;
         }
         this.mcArrows.visible = param1;
         this.txtTitle.visible = param1;
         this.mcBackground.visible = param1;
      }
      
      public function set CommodityData(param1:CommodityStaticData) : void
      {
         var _loc3_:Number = NaN;
         var _loc4_:ProgressBarCheatExtension = null;
         var _loc2_:Boolean = this.mCommodityData !== param1;
         this.mCommodityData = param1;
         if(Boolean(!this.mCommodityData) && Boolean(this.btnSolve.mcIcon) && Boolean(this.btnSolve.mcIcon.resourceId))
         {
            this.btnSolve.mcIcon.LoadImage(null);
         }
         this.mcBuffIcon.visible = false;
         this.mVisibleBuffId = "";
         this.btnSolve.addEventListener(PushButtonEvent.CLICK,this.OnSolveButtonClick,false,0,true);
         this.btnSolve.mcIcon.mouseEnabled = false;
         this.btnSolve.mcIcon.mouseChildren = false;
         this.mcBuffIcon.mcImage.mouseEnabled = false;
         this.btnTooltip = this.btnSolve.GetExtension(TooltipExtension) as TooltipExtension;
         this.containerTooltip = GetExtension(TooltipExtension) as TooltipExtension;
         this.barTooltip = this.mcBar.GetExtension(TooltipExtension) as TooltipExtension;
         this.btnTooltip.CustomTooltip = IconTooltip;
         this.containerTooltip.CustomTooltip = IconTooltip;
         this.barTooltip.CustomTooltip = IconTooltip;
         this.btnTooltip.Margins = new Margin(0,0,-(SimInfoMotivePanelTunables.TOOLTIP_Y_OFFSET + this.btnSolve.y),0);
         this.containerTooltip.Margins = new Margin(0,0,-(SimInfoMotivePanelTunables.TOOLTIP_Y_OFFSET + this.y),0);
         this.barTooltip.Margins = new Margin(0,0,-(SimInfoMotivePanelTunables.TOOLTIP_Y_OFFSET + this.mcBar.y),0);
         if(param1)
         {
            this.mRenderStyle = param1.ui_render_style;
            _loc3_ = param1.ui_render_style == CommodityStaticData.MOTIVE_UI_STYLE_DEFAULT ? 0.07 : 0.025;
            this.mcBar.SetRange(param1.min_value_tuning,param1.max_value_tuning,_loc3_);
            _loc4_ = GetExtension(ProgressBarCheatExtension) as ProgressBarCheatExtension;
            if(this.mRenderStyle == CommodityStaticData.MOTIVE_UI_STYLE_ORB)
            {
               _loc4_.mType = ProgressBarCheatExtension.TYPE_VERTICAL_BAR;
            }
            _loc4_.mcContainer = this;
            _loc4_.mcProgressBar = this.mcBar;
            _loc4_.mID = param1.commodity_id;
            _loc4_.mMinValue = param1.min_value_tuning;
            _loc4_.mMaxValue = param1.max_value_tuning;
            _loc4_.mSetByClickGameService = "stats.set_commodity_percent";
            _loc4_.mSetByDialogGameService = "stats.set_commodity";
            _loc4_.mDialogTitle = "Set Motive";
            _loc4_.SetupBarClickListener();
            if(_loc2_)
            {
               this.mState = 0;
            }
         }
      }
      
      public function get Id() : String
      {
         if(this.mCommodityData)
         {
            return this.mCommodityData.commodity_id;
         }
         return null;
      }
      
      public function get State() : uint
      {
         return this.mState;
      }
      
      public function HandleBuffUpdate(param1:BuffInfo) : void
      {
         var _loc3_:Boolean = false;
         var _loc4_:int = 0;
         var _loc5_:int = 0;
         var _loc6_:BuffInfo = null;
         var _loc7_:BuffInfo = null;
         var _loc8_:String = null;
         var _loc9_:MoodStaticData = null;
         var _loc10_:TooltipExtension = null;
         var _loc11_:MoodStaticData = null;
         var _loc2_:Boolean = Boolean(param1) && param1.ContainsOverlayType(BuffMotiveOverlay.BUFF_MOTIVE_OVERLAY_IMPACTING_MOTIVE);
         if(_loc2_)
         {
            switch(param1.update_type)
            {
               case BuffInfo.BUFF_UPDATE_TYPE_ADD:
                  this.mBuffsImpactingMotive.push(param1);
                  break;
               case BuffInfo.BUFF_UPDATE_TYPE_UPDATE:
                  _loc3_ = false;
                  _loc4_ = 0;
                  _loc5_ = int(this.mBuffsImpactingMotive.length);
                  while(_loc4_ < _loc5_)
                  {
                     _loc6_ = this.mBuffsImpactingMotive[_loc4_] as BuffInfo;
                     if(_loc6_.buff_id == param1.buff_id)
                     {
                        _loc3_ = true;
                        break;
                     }
                     _loc4_++;
                  }
                  if(!_loc3_)
                  {
                     this.mBuffsImpactingMotive.push(param1);
                  }
                  break;
               case BuffInfo.BUFF_UPDATE_TYPE_REMOVE:
                  _loc4_ = 0;
                  _loc5_ = int(this.mBuffsImpactingMotive.length);
                  while(_loc4_ < _loc5_)
                  {
                     _loc6_ = this.mBuffsImpactingMotive[_loc4_] as BuffInfo;
                     if(_loc6_.buff_id == param1.buff_id)
                     {
                        this.mBuffsImpactingMotive.splice(_loc4_,1);
                        break;
                     }
                     _loc4_++;
                  }
            }
         }
         if(!this.mbShowBuffIcon || !param1)
         {
            this.mcBuffIcon.visible = false;
            this.mVisibleBuffId = "";
         }
         else if(param1.update_type == BuffInfo.BUFF_UPDATE_TYPE_REMOVE)
         {
            if(Boolean(this.mBuffsImpactingMotive) && this.mBuffsImpactingMotive.length > 0)
            {
               if(param1.buff_id == this.mVisibleBuffId)
               {
                  _loc7_ = this.mBuffsImpactingMotive[0];
                  this.mVisibleBuffId = _loc7_.buff_id;
                  this.mcBuffIcon.visible = true;
                  this.mcBuffIcon.mcImage.LoadImage(_loc7_.BuffIcon);
                  _loc8_ = "";
                  _loc9_ = MoodStaticData.GetMoodByKey(_loc7_.MoodKey);
                  if(_loc9_)
                  {
                     _loc8_ = _loc9_.GetPortraitFrame(0);
                  }
                  _loc10_ = this.mcBuffIcon.GetExtension(TooltipExtension) as TooltipExtension;
                  _loc10_.Data = {
                     "info":_loc7_,
                     "mood":_loc8_
                  };
               }
            }
            else if(param1.buff_id == this.mVisibleBuffId)
            {
               this.mcBuffIcon.visible = false;
               this.mVisibleBuffId = "";
            }
         }
         else if(param1.update_type == BuffInfo.BUFF_UPDATE_TYPE_ADD || param1.update_type == BuffInfo.BUFF_UPDATE_TYPE_UPDATE)
         {
            if((!this.mcBuffIcon.visible || !_loc2_) && this.mVisibleBuffId != param1.buff_id)
            {
               this.mVisibleBuffId = param1.buff_id;
               this.mcBuffIcon.visible = true;
               this.mcBuffIcon.mcImage.LoadImage(param1.BuffIcon);
               _loc8_ = "";
               _loc11_ = MoodStaticData.GetMoodByKey(param1.MoodKey);
               if(_loc11_)
               {
                  _loc8_ = _loc11_.GetPortraitFrame(0);
               }
               _loc10_ = this.mcBuffIcon.GetExtension(TooltipExtension) as TooltipExtension;
               _loc10_.Data = {
                  "info":param1,
                  "mood":_loc8_
               };
            }
         }
         if(param1)
         {
            if(param1.ContainsOverlayCommodityId(this.Id))
            {
               if(param1.ContainsOverlayType(BuffMotiveOverlay.BUFF_MOTIVE_OVERLAY_POWER_WARNING))
               {
                  this.ShowOverlay(param1.update_type == BuffInfo.BUFF_UPDATE_TYPE_ADD || param1.update_type == BuffInfo.BUFF_UPDATE_TYPE_UPDATE);
                  dispatchEvent(new GenericEvent(UPDATE_MOTIVE_PANEL_WARNING_EVENT,true));
               }
            }
         }
         else
         {
            this.ShowOverlay(false);
         }
      }
      
      public function Update(param1:CommodityProgressUpdate, param2:Boolean) : Boolean
      {
         var _loc4_:uint = 0;
         var _loc8_:Boolean = false;
         var _loc10_:String = null;
         var _loc3_:CommodityStaticData = this.mCommodityData;
         if(!_loc3_)
         {
            return false;
         }
         _loc4_ = param1.commodity_state_index;
         var _loc5_:CommodityState = _loc3_.commodity_states[_loc4_] as CommodityState;
         if(!_loc5_)
         {
            return false;
         }
         if(!param2)
         {
            _loc10_ = null;
            if(_loc4_ > this.mState)
            {
               _loc10_ = _loc5_.ui_container_animation_increasing;
            }
            else if(_loc4_ < this.mState)
            {
               _loc10_ = _loc5_.ui_container_animation_decreasing;
            }
            if(Boolean(this.mcStateChangeOverlay) && Boolean(_loc10_))
            {
               this.mcStateChangeOverlay.gotoAndPlay(_loc10_);
            }
         }
         this.mState = _loc4_;
         this.mChangeRate = param1.rate_of_change;
         var _loc6_:Number = param1.current_value;
         var _loc7_:Number = this.Value;
         this.mcBar.SetValue(_loc6_,!param2);
         this.SetBarColor(!param2);
         if(this.mcBar.Maximum == this.Value || this.mcBar.Minimum == this.Value)
         {
            _loc8_ = this.SetChangeRateFrame(0);
         }
         else if(!param2 && !param1.is_rate_change)
         {
            _loc8_ = this.SetChangeRateFrame(_loc6_ - _loc7_);
         }
         else
         {
            _loc8_ = this.SetChangeRateFrame(this.mChangeRate);
         }
         if(param2)
         {
            this.btnSolve.mcIcon.LoadImage(null);
         }
         var _loc9_:ResourceKey = _loc5_.GetIcon(GameplayStateData.AllTraitIds);
         if(this.mbShowSolveButton && _loc9_.instance != "0")
         {
            this.btnSolve.mcIcon.visible = true;
            this.btnSolve.mcIcon.LoadImage(_loc9_.instance);
         }
         this.SetupTooltipData(this.btnTooltip);
         this.SetupTooltipData(this.containerTooltip);
         this.SetupTooltipData(this.barTooltip);
         this.txtTitle.htmlText = this.mCommodityData.GetCommodityName(GameplayStateData.AllTraitIds).toString();
         dispatchEvent(new GenericEvent("UpdateMotivePanelButton",true,false,true));
         return _loc8_;
      }
      
      public function SetupTooltipData(param1:TooltipExtension) : void
      {
         var _loc5_:SimPB = null;
         var _loc6_:SimPB = null;
         var _loc7_:Boolean = false;
         var _loc8_:Object = null;
         var _loc9_:Array = null;
         var _loc10_:CommodityState = null;
         var _loc11_:String = null;
         var _loc2_:CommodityStaticData = this.mCommodityData;
         if(!_loc2_)
         {
            param1.Data = null;
            return;
         }
         var _loc3_:Array = GameplayStateData.SelectableSims;
         var _loc4_:String = GameplayStateData.ActiveSimId;
         for each(_loc6_ in _loc3_)
         {
            if(_loc6_.id == _loc4_)
            {
               _loc5_ = _loc6_;
               break;
            }
         }
         _loc7_ = !_loc5_ || !_loc5_.InZone || _loc5_.at_work || TutorialMode.IsFTUE();
         this.btnSolve.enabled = !_loc7_;
         _loc8_ = GameplayStateData.ActiveSimToken;
         _loc9_ = GameplayStateData.AllTraitIds;
         _loc10_ = _loc2_.commodity_states[this.mState] as CommodityState;
         _loc11_ = _loc10_.GetDescription(_loc9_).toString(_loc8_);
         if(param1 == this.btnTooltip && !_loc7_)
         {
            _loc11_ = Keys.GENERIC_NEWLINE.toString(_loc11_,KeysGP.SIM_INFO_MOTIVES_AUTOSOLVE.toString());
         }
         var _loc12_:Array = _loc10_.GetTooltipIcons(_loc9_);
         param1.Data = {
            "type":Tooltip.TYPE_TITLE_DESCRIPTION,
            "title":_loc2_.GetCommodityName(_loc9_),
            "text":_loc11_,
            "icons":_loc12_
         };
      }
      
      public function get CurrentCommodityState() : CommodityState
      {
         return this.mCommodityData ? this.mCommodityData.commodity_states[this.mState] as CommodityState : null;
      }
      
      public function get IsCommodityInDistress() : Boolean
      {
         var _loc2_:int = 0;
         if(!this.mCommodityData)
         {
            return false;
         }
         var _loc1_:CommodityState = this.mCommodityData.commodity_states[this.mState] as CommodityState;
         if(_loc1_)
         {
            _loc2_ = _loc1_.fill_level;
            if(_loc2_ > CommodityState.FILL_LEVEL_NO_FILL && _loc2_ <= CommodityState.FILL_LEVEL_DISTRESS)
            {
               return true;
            }
         }
         switch(this.mCommodityData.ui_distress_threshold_operator)
         {
            case CommodityStaticData.OPERATOR_GREATER:
               return this.Value > this.mCommodityData.ui_distress_threshold_value;
            case CommodityStaticData.OPERATOR_GREATER_OR_EQUAL:
               return this.Value >= this.mCommodityData.ui_distress_threshold_value;
            case CommodityStaticData.OPERATOR_EQUAL:
               return this.Value == this.mCommodityData.ui_distress_threshold_value;
            case CommodityStaticData.OPERATOR_NOTEQUAL:
               return this.Value != this.mCommodityData.ui_distress_threshold_value;
            case CommodityStaticData.OPERATOR_LESS_OR_EQUAL:
               return this.Value <= this.mCommodityData.ui_distress_threshold_value;
            case CommodityStaticData.OPERATOR_LESS:
               return this.Value < this.mCommodityData.ui_distress_threshold_value;
            default:
               return false;
         }
      }
      
      public function get Value() : Number
      {
         return this.mcBar.Value;
      }
      
      public function SetChangeRateFrame(param1:Number) : Boolean
      {
         var _loc2_:CommodityStaticData = this.mCommodityData;
         if(!_loc2_)
         {
            return false;
         }
         var _loc3_:Boolean = this.mcArrows.visible;
         this.mcArrows.visible = true;
         var _loc4_:Tween = this.mActiveArrowTween;
         this.mCurrentDeltaMinutes = 0;
         var _loc5_:String = this.mcArrows.currentFrameLabel;
         if(param1 < _loc2_.negative_triple_arrow_threshold)
         {
            this.PlayArrowAnimation("negative_triple");
         }
         else if(param1 < _loc2_.negative_double_arrow_threshold)
         {
            this.PlayArrowAnimation("negative_double");
         }
         else if(param1 < _loc2_.negative_single_arrow_threshold)
         {
            _loc4_ = this.mPassiveArrowTween;
            this.PlayArrowAnimation("negative_single");
         }
         else if(param1 > _loc2_.positive_triple_arrow_threshold)
         {
            if(this.mRenderStyle == CommodityStaticData.MOTIVE_UI_STYLE_LONG)
            {
               this.PlayArrowAnimation("long_positive_triple");
            }
            else
            {
               this.PlayArrowAnimation("positive_triple");
            }
         }
         else if(param1 > _loc2_.positive_double_arrow_threshold)
         {
            if(this.mRenderStyle == CommodityStaticData.MOTIVE_UI_STYLE_LONG)
            {
               this.PlayArrowAnimation("long_positive_double");
            }
            else
            {
               this.PlayArrowAnimation("positive_double");
            }
         }
         else
         {
            if(param1 <= _loc2_.positive_single_arrow_threshold)
            {
               this.mcArrows.visible = false;
               this.mNextTween = this.mDummyArrowTween;
               return _loc3_ != this.mcArrows.visible;
            }
            if(this.mRenderStyle == CommodityStaticData.MOTIVE_UI_STYLE_LONG)
            {
               this.PlayArrowAnimation("long_positive_single");
            }
            else
            {
               this.PlayArrowAnimation("positive_single");
            }
         }
         if(_loc4_ != this.mCurrentTween && _loc4_ != this.mNextTween)
         {
            this.mNextTween = _loc4_;
         }
         return _loc5_ != this.mcArrows.currentFrameLabel;
      }
      
      protected function PlayArrowAnimation(param1:String) : void
      {
         if(this.mbArrowsUseLongAnimations)
         {
            this.mcArrows.gotoAndPlay(param1);
         }
         else
         {
            this.mcArrows.gotoAndStop(param1);
         }
      }
      
      public function CreateArrowTween(param1:TweenParams, param2:Number, param3:Boolean) : void
      {
         var _loc4_:Tween = null;
         _loc4_ = Tween.CreateFromParams(param1,this.mcArrows,null,param2);
         _loc4_.addEventListener(TweenEvent.TWEEN_COMPLETE,this.OnTweenComplete,false,0,true);
         if(param3)
         {
            this.mActiveArrowTween = _loc4_;
         }
         else
         {
            this.mPassiveArrowTween = _loc4_;
            this.mCurrentTween = _loc4_;
            this.mNextTween = _loc4_;
         }
      }
      
      public function StartArrowAnimation(param1:Boolean, param2:int) : void
      {
         this.mcArrows.alpha = this.mCurrentTween == this.mActiveArrowTween ? SimInfoMotivePanelTunables.ACTIVE_ARROW_ALPHA_LOW : SimInfoMotivePanelTunables.PASSIVE_ARROW_ALPHA_LOW;
         var _loc3_:Tween = param1 ? this.mNextTween : this.mCurrentTween;
         var _loc4_:Number = SimInfoMotivePanelTunables.GetInitialDelayForContainer(param2);
         _loc3_.ChangeDelay(_loc4_);
         _loc3_.Start();
         if(Time.Paused)
         {
            _loc3_.Pause();
         }
      }
      
      public function StopArrowAnimation() : void
      {
         this.mPassiveArrowTween.Stop(false,true);
         this.mActiveArrowTween.Stop(false,true);
      }
      
      public function OnTweenComplete(param1:TweenEvent) : void
      {
         var _loc2_:Tween = this.mNextTween;
         _loc2_.ChangeDelay(SimInfoMotivePanelTunables.DELAY_AFTER_FIRST_PLAY);
         _loc2_.Start();
         this.mCurrentTween = _loc2_;
         if(Time.Paused)
         {
            _loc2_.Pause();
         }
      }
      
      public function HandleGameSpeedChanged(param1:Boolean) : void
      {
         var _loc2_:Tween = this.mCurrentTween;
         if(param1)
         {
            _loc2_.Pause();
         }
         else
         {
            _loc2_.Play();
         }
      }
      
      public function ShowOverlay(param1:Boolean, param2:Boolean = false) : void
      {
         if(!this.mcOverlay)
         {
            return;
         }
         this.mbOverlayActive = param1;
         var _loc3_:LoopingAnimExtension = this.mcOverlay.GetExtension(LoopingAnimExtension) as LoopingAnimExtension;
         if(param1)
         {
            _loc3_.Start();
         }
         else
         {
            _loc3_.Stop(param2);
         }
      }
      
      public function UpdateValueFromDeltaMinutes(param1:Number, param2:Boolean) : Boolean
      {
         var _loc6_:Number = NaN;
         var _loc3_:Number = this.mCurrentDeltaChange + this.mChangeRate * param1;
         var _loc4_:Number = DELTA_CHANGE_DRAW_THRESHOLD;
         var _loc5_:Boolean = false;
         if(_loc3_ > _loc4_ || _loc3_ < -_loc4_)
         {
            if(this.mcBar.IsAnimating)
            {
               return false;
            }
            _loc6_ = this.Value;
            this.mcBar.SetValue(this.Value + _loc3_,false);
            this.SetBarColor(!param2);
            if(this.mcBar.Maximum == this.Value || this.mcBar.Minimum == this.Value)
            {
               _loc5_ = this.SetChangeRateFrame(0);
            }
            else if(!param2)
            {
               _loc5_ = this.SetChangeRateFrame(this.mChangeRate);
            }
            this.mCurrentDeltaChange = 0;
         }
         else
         {
            this.mCurrentDeltaChange = _loc3_;
            if(this.mChangeRate == 0)
            {
               this.mCurrentDeltaMinutes += param1;
               if(this.mCurrentDeltaMinutes > SimInfoMotivePanelTunables.ARROW_TIMEOUT_MINUTES)
               {
                  this.SetChangeRateFrame(0);
               }
            }
         }
         return _loc5_;
      }
      
      protected function GetClipColor(param1:Number) : uint
      {
         return this.mCommodityData ? uint(this.CurrentCommodityState.GetFillColor() & 0xFFFFFF) : 0;
      }
      
      protected function GetBackgroundColor(param1:Number) : uint
      {
         return this.mCommodityData ? uint(this.CurrentCommodityState.background_color & 0xFFFFFF) : 0;
      }
      
      protected function SetBarColor(param1:Boolean) : void
      {
      }
      
      public function GetBarColor() : uint
      {
         return 0;
      }
      
      public function Clear() : void
      {
         this.txtTitle.htmlText = "";
         this.CommodityData = null;
         this.visible = false;
      }
      
      public function SetYPosition(param1:Number) : void
      {
         var _loc3_:Number = NaN;
         var _loc2_:Array = [this.mcBar,this.btnSolve,this.btnSolve.mcIcon,this.mcBuffIcon,this.mcBuffIcon.mcImage,this.txtTitle,this.mcBackground];
         var _loc4_:int = 0;
         var _loc5_:int = _loc2_.length;
         while(_loc4_ < _loc5_)
         {
            if(_loc2_[_loc4_])
            {
               _loc3_ = _loc2_[_loc4_].y - y;
               _loc2_[_loc4_].y = param1 + _loc3_;
            }
            _loc4_++;
         }
         y = param1;
      }
      
      public function SetBackgroundLabel(param1:int, param2:int) : void
      {
         var _loc3_:String = null;
         _loc3_ = "Background" + param2 + param1;
         this.mcBackground.gotoAndStop(_loc3_);
      }
      
      public function SaveOriginalYValues() : void
      {
         this.mOriginalY = y;
         this.mOriginalBarY = this.mcBar.y;
         this.mOriginalBtnSolveY = this.btnSolve.y;
         this.mOriginalBtnSolveIconY = this.btnSolve.mcIcon.y;
         this.mOriginalBuffIconY = this.mcBuffIcon.y;
         this.mOriginalBuffIconImageY = this.mcBuffIcon.mcImage.y;
         this.mOriginalTxtTitleY = this.txtTitle.y;
         this.mOriginalBackgroundY = this.mcBackground.y;
      }
      
      public function LoadOriginalYValues() : void
      {
         y = this.mOriginalY;
         this.mcBar.y = this.mOriginalBarY;
         this.btnSolve.y = this.mOriginalBtnSolveY;
         this.btnSolve.mcIcon.y = this.mOriginalBtnSolveIconY;
         this.mcBuffIcon.y = this.mOriginalBuffIconY;
         this.mcBuffIcon.mcImage.y = this.mOriginalBuffIconImageY;
         this.txtTitle.y = this.mOriginalTxtTitleY;
         this.mcBackground.y = this.mOriginalBackgroundY;
      }
      
      protected function OnSolveButtonClick(param1:PushButtonEvent) : void
      {
         if(!this.mCommodityData)
         {
            return;
         }
         CommunicationManager.CallGameService("PostServerCommand",{
            "command":"stats.solve_motive",
            "commandArgs":[this.mCommodityData.commodity_id]
         });
      }
   }
}

