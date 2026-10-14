package widgets.ObjectBoundElements.elements
{
   import flash.events.TimerEvent;
   import flash.utils.Timer;
   import gamedata.BuildBuy.shared.BuildBuyStateData;
   import gamedata.GameContent;
   import gamedata.Gameplay.shared.RankedStatisticProgressUpdate;
   import gamedata.Gameplay.shared.definitions.FameStaticData;
   import gamedata.shared.ManagerObjectId;
   import gamedata.shared.SimInfoUpdate;
   import olympus.core.bind3d.element.ObjectBoundElement;
   import olympus.core.bind3d.io.IElementCommunication;
   import olympus.io.CommunicationManager;
   import olympus.localization.LocKey;
   import olympus.motion.Tween;
   import olympus.objects.RelationshipInfo;
   import olympus.objects.RelationshipTrackInfo;
   import olympus.core.TooltipManager;
   import olympus.objects.SimIdentity;
   import widgets.Gameplay.constants.GameplayTunables;
   import widgets.Gameplay.constants.PlumbbobVisibilityFlag;
   import widgets.Gameplay.controls.SimDetailPanel;
   
   [Embed(source="/_assets/assets.swf", symbol="symbol234")]
   public class SimHeadline extends ObjectBoundElement
   {
      
      public var mcSimDetail:SimDetailPanel;
      
      protected var mTimerPanelShowDelay:Timer;
      
      protected var mNameplateShowTween:Tween;
      
      protected var mNameplateHideTween:Tween;
      
      protected var mTimerNameplateHideDelay:Timer;
      
      protected var mTimerNameplateShowDelay:Timer;
      
      protected var mSimIdentity:SimIdentity;
      
      protected var mAttachedManagerId:int;
      
      protected var mbNameplateShown:Boolean = false;
      
      protected var mSimHeadline:LocKey;
      
      public function SimHeadline()
      {
         super();
         this.mcSimDetail.alpha = 0;
         this.mTimerNameplateHideDelay = new Timer(GameplayTunables.NAMEPLATE_HIDE_DELAY,1);
         this.mTimerNameplateHideDelay.addEventListener(TimerEvent.TIMER_COMPLETE,this.OnHideDelayTimerComplete,false,0,true);
         this.mTimerNameplateShowDelay = new Timer(GameplayTunables.NAMEPLATE_SHOW_DELAY,1);
         this.mTimerNameplateShowDelay.addEventListener(TimerEvent.TIMER_COMPLETE,this.OnShowDelayTimerComplete,false,0,true);
      }
      
      override public function RegisterMessageListeners(param1:IElementCommunication) : void
      {
         super.RegisterMessageListeners(param1);
         param1.AddMessageListener("SetActive",this.HandleSetActive);
         param1.AddMessageListener("ShowSimNameplate",this.HandleShowSimNameplate,true);
         param1.AddMessageListener("HideSimNameplate",this.HandleHideSimNameplate);
         param1.AddMessageListener("SimInfoUpdate",this.HandleSimInfoUpdate);
         param1.AddMessageListener("UpdateSimRelationship",this.HandleUpdateRelationshipInfo);
         param1.AddMessageListener("SetSimHeadline",this.HandleSetSimHeadline);
      }
      
      override protected function OnObjectAttached() : void
      {
         super.OnObjectAttached();
         this.mNameplateHideTween = Tween.CreateFromParams(GameplayTunables.HEADLINE_FADE_OUT_TWEEN_PARAMS,this.mcSimDetail);
         this.mNameplateShowTween = Tween.CreateFromParams(GameplayTunables.HEADLINE_FADE_IN_TWEEN_PARAMS,this.mcSimDetail);
         var _loc1_:String = ObjectID;
         this.mSimIdentity = new SimIdentity(CommunicationManager.CallGameService("GetSimNameInfo",{"simId":_loc1_}));
         var _loc2_:Object = CommunicationManager.CallGameService("GetSimHeadline",_loc1_);
         this.HandleSetSimHeadline(_loc2_);
         this.mcSimDetail.visible = false;
      }
      
      override protected function OnObjectDetached() : void
      {
         super.OnObjectDetached();
         this.mTimerNameplateHideDelay.reset();
         this.mTimerNameplateShowDelay.reset();
         this.mNameplateHideTween.Stop();
         this.mNameplateShowTween.Stop();
         this.mcSimDetail.visible = false;
      }
      
      override public function Show() : void
      {
         if(this.mAttachedManagerId == ManagerObjectId.MGR_SIM_INFO)
         {
            CommunicationManager.CallGameService("SetPlumbbobVisibility",{
               "simId":ObjectID,
               "entity":PlumbbobVisibilityFlag.NAMEPLATE,
               "visible":false
            },true);
         }
         var _loc1_:Object = CommunicationManager.CallGameService("GetSimHeadline",ObjectID);
         this.HandleSetSimHeadline(_loc1_);
         this.mcSimDetail.visible = true;
         super.Show();
      }
      
      override public function Hide() : void
      {
         if(this.mbNameplateShown)
         {
            this.HandleHideSimNameplate(true);
            return;
         }
         if(this.mAttachedManagerId == ManagerObjectId.MGR_SIM_INFO)
         {
            CommunicationManager.CallGameService("SetPlumbbobVisibility",{
               "simId":ObjectID,
               "entity":PlumbbobVisibilityFlag.NAMEPLATE,
               "visible":true
            },true);
         }
         this.mcSimDetail.visible = false;
         super.Hide();
      }
      
      protected function ShowNameplate() : void
      {
         this.Show();
         this.mNameplateHideTween.Stop();
         this.mNameplateShowTween.Start();
         this.A11yAnnounceNameplate();
      }

      public function A11yAnnounceNameplate() : void
      {
         try
         {
            if(this.mcSimDetail == null)
            {
               return;
            }
            TooltipManager.getInstance().A11yAnnounceDisplay(this.mcSimDetail,"a11y.widget_enc");
         }
         catch(e:Error)
         {
         }
      }
      
      protected function HideNameplate() : void
      {
         this.Hide();
         this.mNameplateShowTween.Stop();
         this.mNameplateHideTween.Start();
      }
      
      protected function HandleSetActive(param1:Boolean) : void
      {
         var _loc2_:Boolean = this.mSimIdentity.isActive;
         this.mSimIdentity.isActive = param1;
         if(this.mbNameplateShown)
         {
            if(!param1)
            {
               this.HandleShowSimNameplate(null);
            }
            else
            {
               this.HandleHideSimNameplate(true);
            }
         }
      }
      
      protected function HandleShowSimNameplate(param1:Object) : void
      {
         var _loc2_:int = 0;
         var _loc3_:Array = null;
         var _loc4_:Object = null;
         var _loc5_:Object = null;
         var _loc6_:Object = null;
         var _loc7_:Object = null;
         var _loc8_:RelationshipInfo = null;
         if(param1)
         {
            this.mAttachedManagerId = param1["managerId"];
         }
         this.mbNameplateShown = true;
         if(this.mAttachedManagerId == ManagerObjectId.MGR_SIM_INFO)
         {
            _loc2_ = SimDetailPanel.STYLE_DEFAULT;
            if(Boolean(param1) && "nameplateStyle" in param1)
            {
               _loc2_ = int(param1["nameplateStyle"]);
            }
            this.mcSimDetail.SetStyle(_loc2_);
            this.mcSimDetail.SetSimInfo(this.mSimIdentity);
            if(Boolean(this.mSimHeadline) && this.mSimHeadline.IsValid())
            {
               this.mcSimDetail.SetSimNameSubtitle(this.mSimHeadline.toString());
            }
            else
            {
               this.mcSimDetail.SetSimNameSubtitle(null);
            }
            if(BuildBuyStateData.CurrentVenueInfo.IsBusinessLot && BuildBuyStateData.IsLotOwnedByPlayer)
            {
               _loc4_ = CommunicationManager.CallGameService("GetSimLastBusinessEvent",this.mSimIdentity.simId);
               this.mcSimDetail.SetBusinessData(_loc4_);
            }
            else
            {
               this.mcSimDetail.SetBusinessData(null);
            }
            if(GameContent.HAS_EP06)
            {
               _loc5_ = CommunicationManager.CallGameService("GetSimRankedStatisticUpdate",{
                  "simId":ObjectID,
                  "statId":FameStaticData.GetStaticData().fame_statistic
               });
               this.mcSimDetail.SetFameData(new RankedStatisticProgressUpdate(_loc5_));
            }
            _loc3_ = CommunicationManager.CallGameService("GetSimsClubs",this.mSimIdentity.simId) as Array;
            this.mcSimDetail.SetClubData(_loc3_,this.mSimIdentity.simId);
            if(GameContent.HAS_EP21)
            {
               _loc6_ = CommunicationManager.CallGameService("GetSimDynastyData",this.mSimIdentity.simId);
               this.mcSimDetail.SetDynastyData(_loc6_,this.mSimIdentity.simId);
               _loc7_ = CommunicationManager.CallGameService("GetSimKnownSecretsScandalsSecretData",this.mSimIdentity.simId);
               this.mcSimDetail.SetScandalData(_loc7_);
            }
         }
         else
         {
            this.mcSimDetail.SetClubData(null,ObjectID);
            this.mcSimDetail.SetBusinessData(null);
            this.mcSimDetail.SetFameData(null);
            this.mcSimDetail.SetDynastyData(null,ObjectID);
            this.mcSimDetail.SetScandalData(null);
         }
         if(this.mAttachedManagerId == ManagerObjectId.MGR_SIM_INFO && !this.mSimIdentity.isActive || this.mAttachedManagerId == ManagerObjectId.MGR_OBJECT)
         {
            _loc8_ = new RelationshipInfo(CommunicationManager.CallGameService("GetSimRelationshipInfo",{
               "targetId":ObjectID,
               "targetManagerId":this.mAttachedManagerId
            }));
            this.mcSimDetail.SetRelationshipInfo(_loc8_);
            if(Boolean(_loc8_) && this.mAttachedManagerId == ManagerObjectId.MGR_OBJECT)
            {
               this.mcSimDetail.SetObjectInfo(ObjectID,_loc8_.targetCatalogId,_loc8_);
            }
         }
         this.mcSimDetail.PositionClips();
         this.mTimerNameplateShowDelay.start();
         this.mTimerNameplateHideDelay.reset();
      }
      
      protected function HandleHideSimNameplate(param1:Boolean) : void
      {
         this.mbNameplateShown = false;
         this.mTimerNameplateShowDelay.reset();
         if(param1)
         {
            this.HideNameplate();
         }
         else
         {
            this.mTimerNameplateHideDelay.delay = GameplayTunables.NAMEPLATE_HIDE_DELAY;
            this.mTimerNameplateHideDelay.start();
         }
      }
      
      protected function HandleSimInfoUpdate(param1:Object) : void
      {
         var _loc2_:SimInfoUpdate = new SimInfoUpdate(param1);
         this.mSimIdentity.firstName = _loc2_.firstName;
         this.mSimIdentity.lastName = _loc2_.lastName;
         this.mcSimDetail.SetSimInfo(this.mSimIdentity);
         this.mcSimDetail.PositionClips();
      }
      
      protected function HandleUpdateRelationshipInfo(param1:Object) : void
      {
         var _loc4_:int = 0;
         var _loc5_:Array = null;
         var _loc6_:RelationshipTrackInfo = null;
         if(this.mbNameplateShown)
         {
            return;
         }
         var _loc2_:Boolean = false;
         var _loc3_:RelationshipInfo = new RelationshipInfo(param1);
         if(_loc3_)
         {
            _loc4_ = int(_loc3_.relTracks.length);
            _loc5_ = _loc3_.relTracks.sort(RelationshipInfo.SortRelationshipTracks,Array.NUMERIC);
            for each(_loc6_ in _loc5_)
            {
               if(_loc6_.change != 0)
               {
                  _loc2_ = true;
                  break;
               }
            }
         }
         if(_loc2_)
         {
            this.mTimerNameplateShowDelay.reset();
            this.mTimerNameplateHideDelay.reset();
            this.mTimerNameplateHideDelay.delay = GameplayTunables.NAMEPLATE_LINGER_RELATIONSHIP_CHANGED;
            this.mTimerNameplateHideDelay.start();
         }
      }
      
      protected function HandleSetSimHeadline(param1:Object) : void
      {
         if(Boolean(param1) && "headline" in param1)
         {
            this.mSimHeadline = new LocKey(param1.headline);
            this.mcSimDetail.SetSimNameSubtitle(this.mSimHeadline.toString());
         }
         else
         {
            this.mSimHeadline = null;
            this.mcSimDetail.SetSimNameSubtitle(null);
         }
         this.mcSimDetail.PositionClips();
      }
      
      protected function OnHideDelayTimerComplete(param1:TimerEvent) : void
      {
         this.mTimerNameplateHideDelay.reset();
         this.mTimerNameplateShowDelay.reset();
         this.mTimerNameplateHideDelay.delay = GameplayTunables.NAMEPLATE_HIDE_DELAY;
         this.HideNameplate();
      }
      
      protected function OnShowDelayTimerComplete(param1:TimerEvent) : void
      {
         this.mTimerNameplateShowDelay.reset();
         this.mTimerNameplateHideDelay.reset();
         this.ShowNameplate();
      }
   }
}

