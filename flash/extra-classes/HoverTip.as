package widgets.ObjectBoundElements.elements
{
   import flash.events.TimerEvent;
   import flash.utils.Timer;
   import olympus.core.bind3d.element.ObjectBoundElement;
   import olympus.core.bind3d.io.IElementCommunication;
   import olympus.gamepad.NavManager;
   import olympus.objects.ObjectMetadata;
   import olympus.core.TooltipManager;
   import olympus.io.CommunicationManager;
   import olympus.utils.SystemUtils;
   import widgets.Gameplay.constants.GameplayTunables;
   import widgets.Gameplay.controls.GardeningTipPanel;
   import widgets.Gameplay.controls.HoverTipPanel;
   import widgets.Gameplay.controls.IconTipPanel;
   import widgets.Gameplay.controls.ObjectRelationshipHoverTipPanel;
   
   [Embed(source="/_assets/assets.swf", symbol="symbol392")]
   public class HoverTip extends ObjectBoundElement
   {
      
      public var mcHoverTip:HoverTipPanel;
      
      public var mcGardeningTip:GardeningTipPanel;
      
      public var mcIconTip:IconTipPanel;
      
      public var mcObjectRelationshipHoverTip:ObjectRelationshipHoverTipPanel;
      
      protected var mTimerHoverTipShowDelay:Timer;
      
      protected var mTimerHoverTipHideDelay:Timer;
      
      protected var mHoverTipStyle:int = 1;
      
      public function HoverTip()
      {
         super();
         this.mTimerHoverTipShowDelay = new Timer(GameplayTunables.HOVERTIP_SHOW_DELAY,1);
         this.mTimerHoverTipShowDelay.addEventListener(TimerEvent.TIMER_COMPLETE,this.OnShowDelayTimerComplete);
         this.mTimerHoverTipHideDelay = new Timer(GameplayTunables.HOVERTIP_HIDE_DELAY,1);
         this.mTimerHoverTipHideDelay.addEventListener(TimerEvent.TIMER_COMPLETE,this.OnHideDelayTimerComplete,false,0,true);
         this.mcHoverTip.visible = false;
         this.mcHoverTip.mbTooltip = false;
         this.mcGardeningTip.visible = false;
         this.mcGardeningTip.mbTooltip = false;
         this.mcIconTip.visible = false;
         this.mcIconTip.mbTooltip = false;
         this.mcObjectRelationshipHoverTip.visible = false;
         this.mcObjectRelationshipHoverTip.mbTooltip = false;
      }
      
      override public function RegisterMessageListeners(param1:IElementCommunication) : void
      {
         param1.AddMessageListener("UpdateHoverTip",this.HandleUpdateHoverTip);
         param1.AddMessageListener("ShowHoverTip",this.HandleShowHoverTip,true);
         param1.AddMessageListener("HideHoverTip",this.HandleHideHoverTip);
      }
      
      override protected function OnObjectDetached() : void
      {
         super.OnObjectDetached();
         switch(this.mHoverTipStyle)
         {
            case ObjectMetadata.HOVER_TIP_GARDENING:
               this.mcGardeningTip.Hide(false,0);
               break;
            case ObjectMetadata.HOVER_TIP_ICON_TITLE_DESCRIPTION:
               this.mcIconTip.Hide(false,0);
               break;
            case ObjectMetadata.HOVER_TIP_OBJECT_RELATIONSHIP:
               this.mcObjectRelationshipHoverTip.Hide(false,0);
               break;
            default:
               this.mcHoverTip.Hide(false,0);
         }
         this.mTimerHoverTipShowDelay.reset();
         this.mTimerHoverTipHideDelay.reset();
      }
      
      override public function Show() : void
      {
         this.mTimerHoverTipShowDelay.reset();
         switch(this.mHoverTipStyle)
         {
            case ObjectMetadata.HOVER_TIP_GARDENING:
               this.mcGardeningTip.Show(0);
               break;
            case ObjectMetadata.HOVER_TIP_ICON_TITLE_DESCRIPTION:
               this.mcIconTip.Show(0);
               break;
            case ObjectMetadata.HOVER_TIP_OBJECT_RELATIONSHIP:
               this.mcObjectRelationshipHoverTip.Show(0);
               break;
            default:
               this.mcHoverTip.Show(0);
         }
         super.Show();
         this.A11yAnnounceTip(false);
      }

      public function A11yAnnounceTip(param1:Boolean) : void
      {
         var _loc2_:* = null;
         try
         {
            switch(this.mHoverTipStyle)
            {
               case ObjectMetadata.HOVER_TIP_GARDENING:
                  _loc2_ = this.mcGardeningTip;
                  break;
               case ObjectMetadata.HOVER_TIP_ICON_TITLE_DESCRIPTION:
                  _loc2_ = this.mcIconTip;
                  break;
               case ObjectMetadata.HOVER_TIP_OBJECT_RELATIONSHIP:
                  _loc2_ = this.mcObjectRelationshipHoverTip;
                  break;
               default:
                  _loc2_ = this.mcHoverTip;
            }
            if(_loc2_ == null)
            {
               return;
            }
            if(param1 && !_loc2_.visible)
            {
               return;
            }
            TooltipManager.getInstance().A11yAnnounceDisplay(_loc2_,"a11y.widget_enc");
         }
         catch(e:Error)
         {
         }
      }
      
      override public function Hide() : void
      {
         this.mTimerHoverTipShowDelay.reset();
         this.mTimerHoverTipHideDelay.reset();
         switch(this.mHoverTipStyle)
         {
            case ObjectMetadata.HOVER_TIP_GARDENING:
               this.mcGardeningTip.Hide(false,0);
               break;
            case ObjectMetadata.HOVER_TIP_ICON_TITLE_DESCRIPTION:
               this.mcIconTip.Hide(false,0);
               break;
            case ObjectMetadata.HOVER_TIP_OBJECT_RELATIONSHIP:
               this.mcObjectRelationshipHoverTip.Hide(false,0);
               break;
            default:
               this.mcHoverTip.Hide(false,0);
         }
         super.Hide();
      }
      
      protected function HandleUpdateHoverTip(param1:Object) : void
      {
         var _loc2_:ObjectMetadata = null;
         this.mHoverTipStyle = param1["hover_tip"];
         switch(this.mHoverTipStyle)
         {
            case ObjectMetadata.HOVER_TIP_GARDENING:
               this.mcGardeningTip.SetData(param1);
               break;
            case ObjectMetadata.HOVER_TIP_ICON_TITLE_DESCRIPTION:
               this.mcIconTip.SetData(param1);
               break;
            case ObjectMetadata.HOVER_TIP_OBJECT_RELATIONSHIP:
               _loc2_ = new ObjectMetadata(param1);
               this.mcObjectRelationshipHoverTip.SetData(_loc2_);
               if(_loc2_.rel_override_id != null && _loc2_.rel_override_id != "0")
               {
                  this.mcObjectRelationshipHoverTip.SetObjectId(_loc2_.rel_override_id);
               }
               else
               {
                  this.mcObjectRelationshipHoverTip.SetObjectId(ObjectID);
               }
               break;
            default:
               this.mcHoverTip.SetData(param1);
         }
         this.A11yAnnounceTip(true);
      }
      
      protected function HandleShowHoverTip(param1:Object) : void
      {
         var _loc2_:ObjectMetadata = null;
         this.mHoverTipStyle = param1["hover_tip"];
         if(SystemUtils.UsingController && NavManager.Instance.CurrentWidgetName == "PieMenu")
         {
            return;
         }
         switch(this.mHoverTipStyle)
         {
            case ObjectMetadata.HOVER_TIP_GARDENING:
               this.mcGardeningTip.SetData(param1);
               break;
            case ObjectMetadata.HOVER_TIP_ICON_TITLE_DESCRIPTION:
               this.mcIconTip.SetData(param1);
               break;
            case ObjectMetadata.HOVER_TIP_OBJECT_RELATIONSHIP:
               _loc2_ = new ObjectMetadata(param1);
               this.mcObjectRelationshipHoverTip.SetData(_loc2_);
               if(_loc2_.rel_override_id != null && _loc2_.rel_override_id != "0")
               {
                  this.mcObjectRelationshipHoverTip.SetObjectId(_loc2_.rel_override_id);
               }
               else
               {
                  this.mcObjectRelationshipHoverTip.SetObjectId(ObjectID);
               }
               break;
            default:
               this.mcHoverTip.SetData(param1);
         }
         this.mTimerHoverTipShowDelay.start();
      }
      
      protected function HandleHideHoverTip(param1:Object) : void
      {
         this.mTimerHoverTipHideDelay.start();
      }
      
      protected function OnShowDelayTimerComplete(param1:TimerEvent) : void
      {
         this.Show();
      }
      
      protected function OnHideDelayTimerComplete(param1:TimerEvent) : void
      {
         this.Hide();
      }
      
      override protected function LocalTest() : void
      {
         super.LocalTest();
         var _loc1_:Object = new Object();
         _loc1_["hover_tip"] = 2;
         _loc1_["recipe_name"] = "I\'m a very long recipe name";
         _loc1_["recipe_description"] = "I\'m the recipe description. I\'m a very very long description. I need to be at least 3 lines, so I might copy myself a lot.";
         _loc1_["quality"] = 1;
         _loc1_["servings"] = 2;
         _loc1_["spoiled_time"] = null;
         this.mcHoverTip.SetData(_loc1_);
         this.mcHoverTip.Show(0);
         this.mcHoverTip.x = stage.stageWidth * 0.5;
         this.mcHoverTip.y = stage.stageHeight * 0.75;
      }
   }
}

