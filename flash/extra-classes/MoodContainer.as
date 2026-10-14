package widgets.Gameplay.SimHub.controls
{
   import flash.display.MovieClip;
   import flash.events.Event;
   import flash.events.MouseEvent;
   import flash.text.TextField;
   import flash.text.TextFieldAutoSize;
   import flash.text.TextFormat;
   import gamedata.Dialog.UiPhoneRingMessage;
   import gamedata.Gameplay.Buffs.BuffInfo;
   import gamedata.Gameplay.Buffs.definitions.BuffStaticData;
   import gamedata.Gameplay.shared.GameplayStateData;
   import gamedata.Gameplay.shared.MoodUpdate;
   import gamedata.Gameplay.shared.definitions.MoodStaticData;
   import olympus.audio.Audio;
   import olympus.constants.Alignment;
   import olympus.controls.GUIComponent;
   import olympus.controls.ImageResource;
   import olympus.core.tooltip.Tooltip;
   import olympus.core.TooltipManager;
   import olympus.core.tooltip.TooltipObject;
   import olympus.events.AssetLoaderEvent;
   import olympus.extensions.TutorialTipExtension;
   import olympus.io.CommunicationManager;
   import olympus.localization.Keys;
   import olympus.localization.KeysGP;
   import olympus.localization.LocKey;
   import olympus.math.TimeSpan;
   import olympus.objects.SimPB;
   import olympus.utils.ImageUtils;
   import olympus.utils.MovieClipUtils;
   import olympus.utils.TextUtils;
   import scaleform.gfx.MouseEventEx;
   import scaleform.gfx.TextFieldEx;
   import widgets.Gameplay.constants.GameplayTunables;
   import widgets.shared.constants.TutorialTipUIElement;
   
   [Embed(source="/_assets/assets.swf", symbol="symbol316")]
   public class MoodContainer extends GUIComponent
   {
      
      public var mcOldThumbnail:ImageResource;
      
      public var mcSimContainer:MovieClip;
      
      public var mcMoodTextContainer:MovieClip;
      
      public var mcMoodBkg:GUIComponent;
      
      public var mcMoodArc:MovieClip;
      
      public var mbSpecialMoment:Boolean = false;
      
      protected var mbFirstUpdate:Boolean = true;
      
      protected var mCurrentMood:MoodUpdate;
      
      protected var mCurrentMoodData:MoodStaticData;
      
      protected var mMoodTooltipObj:TooltipObject;
      
      protected var txtMood:TextField;
      
      protected var txtMoodVert:TextField;
      
      protected var mOriginalVertTextFontSize:Object;
      
      protected var mOriginalVertTextPosY:Number;
      
      protected var mOriginalVertTextHeight:Number;
      
      public function MoodContainer()
      {
         var _loc2_:TutorialTipExtension = null;
         addFrameScript(0,this.frame1);
         super();
         this.mouseEnabled = false;
         this.mcSimContainer.mouseEnabled = false;
         this.mcSimContainer.mouseChildren = false;
         this.mcOldThumbnail.mouseEnabled = false;
         this.mcOldThumbnail.mouseChildren = false;
         this.mcMoodTextContainer.mouseEnabled = false;
         this.mcMoodTextContainer.mouseChildren = false;
         this.mcOldThumbnail.visible = false;
         this.txtMood = this.mcMoodTextContainer.txtMood;
         this.txtMood.visible = false;
         this.txtMoodVert = this.mcMoodTextContainer.txtMoodVert;
         this.mOriginalVertTextFontSize = this.txtMoodVert.getTextFormat().size;
         this.mOriginalVertTextPosY = this.txtMoodVert.y;
         this.mOriginalVertTextHeight = this.txtMoodVert.height;
         this.txtMoodVert.visible = false;
         TextFieldEx.setVerticalAlign(this.txtMoodVert,"bottom");
         this.txtMoodVert.autoSize = TextFieldAutoSize.CENTER;
         MovieClipUtils.AddFrameScript(this,"midTransition",this.OnMidTransitionHit);
         this.mcMoodBkg.addEventListener(MouseEvent.CLICK,this.OnMoodClick,false,0,true);
         var _loc1_:TooltipObject = new TooltipObject(this.mcMoodBkg);
         this.addEventListener(MouseEvent.ROLL_OVER,this.HandleMoodRollOver,false,0,true);
         this.addEventListener(MouseEvent.MOUSE_MOVE,this.A11yMoodMouseMove,false,0,true);
         this.addEventListener(MouseEvent.ROLL_OUT,this.A11yMoodMouseOut,false,0,true);
         this.addEventListener(MouseEvent.ROLL_OUT,_loc1_.HandleEvent,false,0,true);
         this.mMoodTooltipObj = _loc1_;
         _loc2_ = this.mcMoodBkg.GetExtension(TutorialTipExtension) as TutorialTipExtension;
         _loc2_.ControlEnum = TutorialTipUIElement.LIVE_CURRENT_SIM_PORTRAIT;
         _loc2_ = this.GetExtension(TutorialTipExtension) as TutorialTipExtension;
         _loc2_.ControlEnum = TutorialTipUIElement.LIVE_EMOTION;
      }
      
      public function SetMood(param1:MoodUpdate) : void
      {
         var _loc3_:String = null;
         if(!param1)
         {
            this.mcSimContainer.mcIcon.LoadImage(null);
            this.mbFirstUpdate = true;
            return;
         }
         this.mCurrentMood = param1;
         var _loc2_:MoodStaticData = MoodStaticData.GetMoodByKey(param1.mood_key);
         this.mCurrentMoodData = _loc2_;
         if(_loc2_)
         {
            if(!this.mbFirstUpdate)
            {
               this.mcOldThumbnail.visible = true;
               this.mcSimContainer.visible = false;
               this.mcSimContainer.mcIcon.addEventListener(AssetLoaderEvent.COMPLETE,this.OnThumbnailLoadComplete,false,0,true);
            }
            else
            {
               this.SetMoodInfo();
               _loc3_ = _loc2_.GetPortraitFrame(this.mCurrentMood.mood_intensity);
               _loc3_ = _loc3_.concat("_end");
               this.mcSimContainer.gotoAndStop(_loc3_);
               if(this.mcSimContainer.mcTransition)
               {
                  this.mcSimContainer.mcTransition.visible = false;
                  this.mcSimContainer.mcTransition.stop();
               }
            }
            this.mbFirstUpdate = false;
            this.SetSimPortrait();
         }
      }
      
      public function SetSimPortrait() : void
      {
         var _loc1_:MoodStaticData = this.mCurrentMoodData;
         var _loc2_:ImageResource = this.mcSimContainer.mcIcon as ImageResource;
         this.mcOldThumbnail.LoadImage(_loc2_.resourceId);
         ImageUtils.LoadSimThumbnail(_loc2_,this.mCurrentMood.sim_id,ImageUtils.SIM_THUMBNAIL_TYPE_BUST,null,_loc1_.GetPortraitPose(this.mCurrentMood.mood_intensity),true,null,_loc1_.mood_key);
      }
      
      protected function OnThumbnailLoadComplete(param1:AssetLoaderEvent) : void
      {
         if(this.currentLabel == "midTransition")
         {
            addEventListener(Event.ENTER_FRAME,this.OnEnterFrameMidTransition,false,0,true);
         }
         this.play();
         this.mcSimContainer.mcIcon.removeEventListener(AssetLoaderEvent.COMPLETE,this.OnThumbnailLoadComplete);
      }
      
      protected function OnEnterFrameMidTransition(param1:Event) : void
      {
         if(this.currentFrame == 1)
         {
            removeEventListener(Event.ENTER_FRAME,this.OnEnterFrameMidTransition);
            gotoAndPlay(2);
         }
      }
      
      protected function OnMidTransitionHit() : void
      {
         var _loc1_:MoodStaticData = null;
         _loc1_ = this.mCurrentMoodData;
         this.mcOldThumbnail.visible = false;
         this.mcSimContainer.visible = true;
         var _loc2_:String = _loc1_.GetPortraitFrame(this.mCurrentMood.mood_intensity);
         this.mcSimContainer.gotoAndPlay(_loc2_);
         if(this.mcSimContainer.mcTransition)
         {
            this.mcSimContainer.mcTransition.visible = true;
            this.mcSimContainer.mcTransition.play();
         }
         this.SetMoodInfo();
         if(CommunicationManager.CallGameService("OptionsGetValue",{"name":"MoodChange"}))
         {
            Audio.PlayAudio(_loc1_.GetAudioSting(this.mCurrentMood.mood_intensity));
         }
      }
      
      protected function SetMoodInfo() : void
      {
         var _loc3_:uint = 0;
         var _loc4_:String = null;
         var _loc5_:String = null;
         var _loc6_:String = null;
         var _loc7_:String = null;
         var _loc8_:Boolean = false;
         var _loc9_:String = null;
         var _loc10_:Array = null;
         var _loc11_:TextFormat = null;
         var _loc1_:MoodUpdate = this.mCurrentMood;
         var _loc2_:MoodStaticData = this.mCurrentMoodData;
         if(_loc2_)
         {
            _loc3_ = _loc1_.mood_intensity;
            _loc4_ = _loc2_.GetPortraitFrame(_loc3_);
            _loc5_ = _loc2_.GetMoodName(_loc3_).toUpperCase();
            this.mcMoodBkg.gotoAndPlay(_loc4_);
            if(_loc3_ > 0)
            {
               this.mcMoodArc.visible = true;
               this.mcMoodArc.gotoAndStop(_loc4_);
            }
            else
            {
               this.mcMoodArc.visible = false;
               this.mcMoodArc.stop();
            }
            _loc7_ = _loc2_.GetAgeOverrideDescription(GameplayStateData.SimAge.age,_loc3_);
            if(_loc7_)
            {
               _loc6_ = _loc7_;
            }
            else
            {
               _loc9_ = _loc2_.GetTraitOverrideDescription(GameplayStateData.AllTraitInfo,_loc3_);
               _loc6_ = _loc9_ ? _loc9_ : _loc2_.GetDescription(_loc3_);
            }
            try { TooltipManager.getInstance().A11ySetSilentMood(_loc6_); } catch(a11yError:Error) { }
            this.mA11yMoodDescription = _loc6_ != null ? _loc6_ : "";
            this.mMoodTooltipObj.Initialize({
               "type":Tooltip.TYPE_DESCRIPTION_ONLY,
               "text":_loc6_
            });
            this.mMoodTooltipObj.VerticalAlignment = Alignment.CENTER;
            this.mMoodTooltipObj.HorizontalAlignment = Alignment.RIGHT;
            _loc8_ = CommunicationManager.CallGameService("IsVerticalTextSupported") as Boolean;
            if(!_loc8_)
            {
               if(this.txtMood.text != _loc5_)
               {
                  TextUtils.ResizeTextToFit(this.txtMood,_loc5_,this.txtMood.height,this.txtMood.width,10,false);
               }
               this.txtMood.visible = true;
               this.txtMoodVert.visible = false;
            }
            else
            {
               _loc10_ = _loc5_.split("");
               _loc5_ = _loc10_.join("\n");
               _loc11_ = this.txtMoodVert.getTextFormat();
               _loc11_.size = this.mOriginalVertTextFontSize;
               this.txtMoodVert.defaultTextFormat = _loc11_;
               this.txtMoodVert.y = this.mOriginalVertTextPosY;
               this.txtMoodVert.height = this.mOriginalVertTextHeight;
               this.txtMoodVert.htmlText = _loc5_;
               TextUtils.ShrinkTextToTargetHeight(this.txtMoodVert,_loc5_,this.mOriginalVertTextHeight);
               this.txtMood.visible = false;
               this.txtMoodVert.visible = true;
            }
         }
      }
      
      protected function OnMoodClick(param1:MouseEvent) : void
      {
         var _loc3_:String = null;
         var _loc4_:Boolean = false;
         var _loc5_:Array = null;
         var _loc6_:SimPB = null;
         var _loc2_:MouseEventEx = param1 as MouseEventEx;
         if(_loc2_)
         {
            if(this.mbSpecialMoment)
            {
               CommunicationManager.CallGameService("CameraZoom",GameplayTunables.SPECIAL_MOMENT_ZOOM);
            }
            _loc3_ = this.mCurrentMood.sim_id;
            _loc4_ = false;
            _loc5_ = GameplayStateData.SelectableSims;
            for each(_loc6_ in _loc5_)
            {
               if(_loc6_.id == _loc3_)
               {
                  if(_loc6_.InZone && !_loc6_.at_work)
                  {
                     _loc4_ = true;
                  }
                  break;
               }
            }
            if(_loc4_)
            {
               CommunicationManager.CallGameService("CameraCenterOnObj",{
                  "simId":_loc3_,
                  "follow":_loc2_.buttonIdx == MouseEventEx.RIGHT_BUTTON
               });
            }
         }
      }
      
      private var mA11yOverMoodLabel:Boolean = false;

      public function A11yMoodMouseOut(event:MouseEvent) : void
      {
         this.mA11yOverMoodLabel = false;
      }

      public function A11yMoodMouseMove(event:MouseEvent) : void
      {
         try
         {
            var label:TextField = this.txtMood.visible ? this.txtMood : this.txtMoodVert;
            var inside:Boolean = label != null && label.visible && label.getBounds(stage).contains(event.stageX,event.stageY);
            if(inside && !this.mA11yOverMoodLabel) { this.A11yAnnounceMood(); }
            this.mA11yOverMoodLabel = inside;
         }
         catch(e:Error) { }
      }

      protected function HandleMoodRollOver(param1:MouseEvent) : void
      {
         // The background extends between moodlet icons. Only the visible
         // mood label is an intentional mood hover target.
         try
         {
            if(this.mcMoodTextContainer != null && !this.mcMoodTextContainer.getBounds(stage).contains(param1.stageX,param1.stageY)) { return; }
         }
         catch(a11yMoodHitError:Error) { return; }
         this.A11yMoodMouseMove(param1);
         if(!this.IsPhoneAlertVisible())
         {
            this.mMoodTooltipObj.HandleRollOver(param1);
         }
         else
         {
            this.mMoodTooltipObj.HideTooltip(true);
         }
      }

      public function A11yAnnounceMood() : void
      {
         var _loc1_:String = null;
         var _loc2_:String = null;
         try
         {
            // The mood NAME lives in mcMoodTextContainer, which this class
            // sets mouseEnabled = mouseChildren = false, so the generic
            // hover collector can never see it: only the wide mcMoodBkg is
            // hoverable, and hovering it used to read nothing but the mood
            // DESCRIPTION tooltip (tester report 2026-08-03). Compose the
            // displayed name here instead, exactly like the motive bars do.
            // GetMoodName already folds intensity into the localized name
            // ("Very Flirty" vs "Flirty"), so it matches what is on screen.
            if(this.mCurrentMoodData == null || this.mCurrentMood == null)
            {
               return;
            }
            _loc1_ = this.mCurrentMoodData.GetMoodName(this.mCurrentMood.mood_intensity).toString();
            if(_loc1_ == null || _loc1_.length == 0)
            {
               return;
            }
            _loc2_ = encodeURIComponent(_loc1_);
            _loc2_ = _loc2_.split("'").join("%27");
            _loc2_ = _loc2_.split("(").join("%28");
            _loc2_ = _loc2_.split(")").join("%29");
            _loc2_ = _loc2_.split("!").join("%21");
            // widget channel, so the description behind it is held back by
            // the tooltip delay like any other panel row.
            CommunicationManager.PostServerCommand("a11y.widget_enc",_loc2_);
         }
         catch(e:Error)
         {
         }
      }
      
      private var mA11yMoodDescription:String = "";

      private static var sA11yMoodSeq:int = 0;

      // Control Alt E: the whole mood panel in one reading. SimHub is the
      // only movie defining this class and every EA class named below, so
      // they resolve here; TooltipManager reaches this by name only. Records
      // are separate a11y.mood_enc posts (see narrator.a11y_mood_enc).
      public function A11yReadMood() : void
      {
         var infos:Vector.<BuffInfo> = null;
         var info:BuffInfo = null;
         var seq:String = null;
         var moodName:String = "";
         var moodKey:String = "";
         var count:int = 0;
         var index:int = 0;
         try
         {
            sA11yMoodSeq = sA11yMoodSeq + 1;
            seq = String(sA11yMoodSeq);
            if(this.mCurrentMoodData != null && this.mCurrentMood != null)
            {
               moodName = this.mCurrentMoodData.GetMoodName(this.mCurrentMood.mood_intensity);
               moodKey = String(this.mCurrentMood.mood_key);
            }
            infos = GameplayStateData.AllBuffInfo;
            count = infos != null ? int(infos.length) : 0;
            if(count > 40) { count = 40; }
            this.A11yPostMood(["M",seq,String(count),moodKey,this.A11yPlain(moodName),this.A11yPlain(this.mA11yMoodDescription)]);
            while(index < count)
            {
               info = infos[index];
               if(info != null) { this.A11yPostMood(this.A11yBuffRecord(seq,index,info)); }
               index = index + 1;
            }
            this.A11yPostMood(["E",seq]);
         }
         catch(e:Error)
         {
            if(seq != null) { this.A11yPostMood(["E",seq]); }
         }
      }

      // One moodlet as BuffTooltip.SetData shows it.
      public function A11yBuffRecord(seq:String, index:int, info:BuffInfo) : Array
      {
         var mood:MoodStaticData = null;
         var staticMood:MoodStaticData = null;
         var effect:String = "";
         var boost:String = "";
         var weight:uint = 0;
         var moodKey:String = "";
         try
         {
            weight = info.mood_weight;
            moodKey = info.MoodKey;
            mood = MoodStaticData.GetMoodByKey(moodKey);
            if(mood != null)
            {
               staticMood = mood;
               if(info.mood_type_override != null)
               {
                  boost = KeysGP.SIM_HUB_BUFF_BOOST.toString(mood.GetMoodName(0));
                  staticMood = MoodStaticData.GetMoodByKey(info.StaticMoodKey);
               }
               if(staticMood != null)
               {
                  effect = weight == 0 ? staticMood.GetMoodName(0) : KeysGP.SIM_HUB_BUFF_TITLE.toString(staticMood.GetMoodName(0),weight);
               }
            }
            return ["B",seq,String(index),String(moodKey),info.mood_type_override != null ? "1" : "0",String(weight),this.A11yPlain(info.Name),this.A11yPlain(effect),this.A11yPlain(boost),this.A11yPlain(info.Reason),this.A11yPlain(this.A11yBuffTime(info)),this.A11yPlain(info.Description)];
         }
         catch(e:Error)
         {
         }
         return null;
      }

      // BuffTooltip.ProcessTimeSpanText without its HTML wrapper.
      public function A11yBuffTime(info:BuffInfo) : String
      {
         var span:TimeSpan = null;
         var minutes:uint = 0;
         var timeout:LocKey = null;
         var noNext:LocKey = null;
         var next:BuffStaticData = null;
         var nextName:String = "";
         try
         {
            if(info.timeout == null || info.timeout == "0") { return ""; }
            span = new TimeSpan();
            span.Set(info.TimeLeft);
            minutes = span.ConvertToMinutes();
            if(Boolean(info.transition_into_buff_id) && info.transition_into_buff_id != "0")
            {
               next = BuffStaticData.GetStaticData(info.transition_into_buff_id);
               if(next != null) { nextName = next.name.toString(GameplayStateData.ActiveSimToken); }
            }
            timeout = info.TimeoutString;
            if(timeout != null && timeout.IsValid())
            {
               if(nextName != null && nextName.length > 0) { return timeout.toString(minutes,nextName); }
               noNext = info.TimeoutStringNoNextBuff;
               if(noNext != null && noNext.IsValid()) { return noNext.toString(minutes); }
               return timeout.toString(minutes);
            }
            return Keys.GENERIC_TIMESPAN.toString(minutes);
         }
         catch(e:Error)
         {
         }
         return "";
      }

      // Display text of an EA html string, without the record separator.
      public function A11yPlain(text:String) : String
      {
         var field:TextField = null;
         try
         {
            if(text == null || text.length == 0) { return ""; }
            field = new TextField();
            field.htmlText = text;
            return field.text.split(String.fromCharCode(1)).join(" ");
         }
         catch(e:Error)
         {
         }
         return "";
      }

      public function A11yPostMood(fields:Array) : void
      {
         var text:String = null;
         var payload:String = null;
         try
         {
            if(fields == null) { return; }
            text = fields.join(String.fromCharCode(1));
            if(text.length > 1400) { text = text.substr(0,1400); }
            payload = encodeURIComponent(text);
            payload = payload.split("'").join("%27");
            payload = payload.split("(").join("%28");
            payload = payload.split(")").join("%29");
            payload = payload.split("!").join("%21");
            payload = payload.split("~").join("%7E");
            payload = payload.split("*").join("%2A");
            TooltipManager.getInstance().A11yPostToPython("a11y.mood_enc",payload);
         }
         catch(e:Error)
         {
         }
      }

      protected function IsPhoneAlertVisible() : Boolean
      {
         var _loc2_:UiPhoneRingMessage = null;
         var _loc1_:Object = CommunicationManager.CallGameService("GetPhoneRingInfo",GameplayStateData.ActiveSimId,true);
         if(_loc1_ != null)
         {
            _loc2_ = new UiPhoneRingMessage(_loc1_);
            if(_loc2_.IsAlarmType)
            {
               return true;
            }
         }
         return false;
      }
      
      public function HideMoodTooltip() : void
      {
         this.mMoodTooltipObj.HideTooltip(true);
      }
      
      internal function frame1() : *
      {
         stop();
      }
   }
}

