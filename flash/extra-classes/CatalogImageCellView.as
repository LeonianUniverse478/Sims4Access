package widgets.BuildBuy.controls
{
   import flash.display.MovieClip;
   import flash.display.Sprite;
   import flash.events.MouseEvent;
   import gamedata.BuildBuy.shared.CatalogProduct;
   import gamedata.MTX.constants.MTXState;
   import gamedata.shared.SharedIcons;
   import olympus.audio.Audio;
   import olympus.constants.Alignment;
   import olympus.controls.ImageResource;
   import olympus.extensions.TooltipExtension;
   import olympus.gui.buttons.Button;
   import olympus.io.CommunicationManager;
   
   public class CatalogImageCellView extends Button
   {
      
      public var mcImage:ImageResource;
      
      public var mcOverlayOne:ImageResource;
      
      public var mcOverlayTwo:ImageResource;
      
      public var mcOverlayThree:ImageResource;
      
      public var mcNewOverlay:Sprite;
      
      public var mcIconOverlayAnim:MovieClip;
      
      public var mcPackIcon:ImageResource;
      
      public var mcModdedIcon:MovieClip;
      
      public var mcAdditionalFeatureOverlay:MovieClip;
      
      public var mcHighPlatformOverlay:MovieClip;
      
      public var mcLowPlatformOverlay:MovieClip;
      
      protected var mData:CatalogProduct;
      
      protected var mInitModdedIconPosX:Number = 0;
      
      public function CatalogImageCellView()
      {
         super();
         mAudioExtension.CategoryName = "ThumbnailButton";
      }
      
      override public function get height() : Number
      {
         return mcHitArea.height;
      }
      
      override public function get width() : Number
      {
         return mcHitArea.width;
      }
      
      override protected function ConfigUI() : void
      {
         super.ConfigUI();
         this.mouseChildren = true;
         if(this.mcIconOverlayAnim)
         {
            this.mcPackIcon = this.mcIconOverlayAnim.mcPackIcon;
            this.mcModdedIcon = this.mcIconOverlayAnim.mcModdedIcon;
            this.mInitModdedIconPosX = this.mcModdedIcon.x;
         }
         mAudioExtension.ElementName = "CatagalogCellView";
         addEventListener(MouseEvent.ROLL_OVER,this.A11yOnCellRollOver,false,0,true);
         (GetExtension(TooltipExtension) as TooltipExtension).VerticalAlignment = Alignment.CENTER;
      }
      
      override public function Draw(param1:Object, param2:Object = null) : void
      {
         var _loc3_:CatalogProduct = null;
         _loc3_ = this.mData = param1 as CatalogProduct;
         if(!_loc3_)
         {
            return;
         }
         _loc3_.LoadThumbnail(this.mcImage);
         if(this.mcPackIcon)
         {
            if(_loc3_.packId > 0)
            {
               this.mcPackIcon.visible = true;
               this.mcPackIcon.LoadImage(SharedIcons.GetPackIcon(_loc3_.packId,SharedIcons.SIZE_32));
            }
            else
            {
               this.mcPackIcon.visible = false;
            }
         }
         if(this.mcModdedIcon)
         {
            this.mcModdedIcon.visible = _loc3_.is_modded;
            this.mcModdedIcon.x = this.mcPackIcon.visible ? this.mInitModdedIconPosX : this.mcPackIcon.x;
         }
         if(this.mcNewOverlay)
         {
            this.mcNewOverlay.visible = _loc3_.isNew || _loc3_.mtxState == MTXState.UNLOCKED_NEW;
            if(this.mcNewOverlay.visible && Boolean(this.mcPackIcon))
            {
               this.mcPackIcon.visible = false;
            }
         }
         if(this.mcOverlayOne)
         {
            this.mcOverlayOne.visible = false;
            this.mcOverlayTwo.visible = false;
            this.mcOverlayThree.visible = false;
         }
         if(this.mcAdditionalFeatureOverlay)
         {
            this.mcAdditionalFeatureOverlay.visible = _loc3_.HasAdditionalGameplayFeature();
         }
         if(this.mcLowPlatformOverlay)
         {
            this.mcLowPlatformOverlay.visible = _loc3_.IsModularPlaygroundLowPlatform();
         }
         if(this.mcHighPlatformOverlay)
         {
            this.mcHighPlatformOverlay.visible = _loc3_.IsModularPlaygroundHighPlatform();
         }
         this.RefreshAvailabilityData();
      }
      
      override protected function OnMousePress(param1:MouseEvent) : void
      {
         super.OnMousePress(param1);
         if(!enabled)
         {
            mAudioExtension.Dispatch(Audio.CUSTOM);
         }
      }
      
      protected function A11yOnCellRollOver(param1:MouseEvent) : void
      {
         var _loc2_:String = null;
         var _loc3_:String = null;
         var _loc4_:Array = null;
         var _loc5_:int = 0;
         var _loc6_:String = null;
         try
         {
            if(!this.mData)
            {
               return;
            }
            _loc2_ = this.mData.Name;
            // Instance items (player paintings, crafted food, books in
            // the household inventory grid and its stack flyout) share
            // ONE catalog product, so Name is the generic base object
            // ("Monochromatic Sea Monster") for every instance; the
            // per-instance title lives in the metadata block. Lead with
            // it when present (user request 2026-08-20). custom_name is
            // a plain String; recipe_name/header are LocKeys whose
            // toString() localizes, the same way EA's Name getter
            // resolves its LocKey.
            try
            {
               if(this.mData.metadata != null)
               {
                  if(this.mData.metadata.custom_name != null && this.mData.metadata.custom_name.length > 0)
                  {
                     _loc6_ = this.mData.metadata.custom_name;
                  }
                  else if(this.mData.metadata.recipe_name != null)
                  {
                     _loc6_ = this.mData.metadata.recipe_name.toString();
                  }
                  else if(this.mData.metadata.header != null)
                  {
                     _loc6_ = this.mData.metadata.header.toString();
                  }
               }
            }
            catch(e1:Error)
            {
               _loc6_ = null;
            }
            if(_loc6_ != null && _loc6_.length > 0)
            {
               _loc2_ = _loc6_;
            }
            if(_loc2_ == null || _loc2_.length == 0)
            {
               return;
            }
            _loc2_ += ". \u00A7" + this.mData.price.toString();
            // Stack count, folded into the line so the xN badge never
            // needs its own announcement. The \u0002qty\u0002 marker is
            // rewritten Python-side to the localized "Quantity N"
            // (bare English here would defeat the language table).
            if(this.mData.count > 1)
            {
               _loc2_ += ". \u0002qty\u0002" + this.mData.count.toString();
            }
            _loc4_ = this.mData.gameplayInfo;
            if(_loc4_ != null)
            {
               _loc5_ = 0;
               while(_loc5_ < _loc4_.length && _loc5_ < 8)
               {
                  if(_loc4_[_loc5_] != null && _loc4_[_loc5_].name != null)
                  {
                     _loc2_ += ". " + _loc4_[_loc5_].name.toString();
                     if(_loc4_[_loc5_].value != 0)
                     {
                        _loc2_ += " " + _loc4_[_loc5_].value.toString();
                     }
                  }
                  _loc5_++;
               }
            }
            _loc3_ = encodeURIComponent(_loc2_);
            _loc3_ = _loc3_.split("'").join("%27");
            _loc3_ = _loc3_.split("(").join("%28");
            _loc3_ = _loc3_.split(")").join("%29");
            _loc3_ = _loc3_.split("!").join("%21");
            CommunicationManager.PostServerCommand("a11y.widget_enc",_loc3_);
            _loc2_ = this.mData.Description;
            if(_loc2_ != null && _loc2_.length > 0)
            {
               _loc3_ = encodeURIComponent(_loc2_);
               _loc3_ = _loc3_.split("'").join("%27");
               _loc3_ = _loc3_.split("(").join("%28");
               _loc3_ = _loc3_.split(")").join("%29");
               _loc3_ = _loc3_.split("!").join("%21");
               CommunicationManager.PostServerCommand("a11y.speak_enc",_loc3_);
            }
         }
         catch(e:Error)
         {
         }
      }

      protected function RefreshAvailabilityData() : void
      {
         enabled = true;
      }
   }
}

