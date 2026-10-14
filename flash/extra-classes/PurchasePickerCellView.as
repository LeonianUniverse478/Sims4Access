package widgets.Pickers.controls.PurchasePicker
{
   import flash.display.MovieClip;
   import flash.display.Sprite;
   import flash.events.Event;
   import flash.events.MouseEvent;
   import flash.display.DisplayObject;
   import flash.text.TextField;
   import flash.text.TextFieldAutoSize;
   import flash.utils.Timer;
   import flash.events.TimerEvent;
   import olympus.io.CommunicationManager;
   import gamedata.BuildBuy.shared.CatalogProduct;
   import gamedata.Gameplay.Pickers.PurchasePickerRowData;
   import gamedata.Gameplay.shared.GameplayStateData;
   import olympus.controls.GUIComponent;
   import olympus.controls.ImageResource;
   import olympus.core.tooltip.Tooltip;
   import olympus.events.PushButtonEvent;
   import olympus.extensions.TooltipExtension;
   import olympus.gamepad.HighlightRequestEvent;
   import olympus.gui.buttons.Button;
   import olympus.gui.events.GUIEvent;
   import olympus.localization.Keys;
   import olympus.localization.KeysGP;
   import olympus.localization.LocKey;
   import olympus.utils.ImageUtils;
   import olympus.utils.SystemUtils;
   import olympus.utils.TextUtils;
   import olympus.views.CellView;
   import widgets.Pickers.constants.PickersTunables;
   
   [Embed(source="/_assets/assets.swf", symbol="symbol106")]
   public class PurchasePickerCellView extends CellView
   {
      
      protected static const EVEN_BACKGROUND:String = "even";
      
      protected static const ODD_BACKGROUND:String = "odd";
      
      public var txtName:TextField;
      
      public var txtCost:TextField;
      
      public var txtNumOwned:TextField;
      
      public var txtDescription:TextField;
      
      public var mcNumContainer:MovieClip;
      
      public var mcIcon:ImageResource;
      
      public var mcTooltipHolder:GUIComponent;
      
      public var mcBackgroundLeft:MovieClip;
      
      public var mcBackgroundMiddle:MovieClip;
      
      public var mcBackgroundRight:MovieClip;
      
      public var mcNumAvailableBackground:GUIComponent;
      
      public var txtNumAvailable:TextField;
      
      protected var mcPriceStrikeThrough:Sprite;
      
      protected var mTooltipExtension:TooltipExtension;
      
      protected var mNumAvailable:int;
      
      protected var txtItemAmount:TextField;
      
      protected var mcItemAmountBackground:MovieClip;
      
      protected var btnIncrease:Button;
      
      protected var btnDecrease:Button;
      
      protected var mMaxTunedSelectable:uint;
      
      public function PurchasePickerCellView()
      {
         addFrameScript(9,this.frame10,19,this.frame20,29,this.frame30,39,this.frame40);
         super();
         this.txtItemAmount = this.mcNumContainer.txtItemAmount;
         this.mcItemAmountBackground = this.mcNumContainer.mcItemAmountBackground;
         this.btnIncrease = this.mcNumContainer.btnIncrease;
         this.btnDecrease = this.mcNumContainer.btnDecrease;
      }
      
      override protected function ConfigUI() : void
      {
         super.ConfigUI();
         this.txtNumAvailable.mouseEnabled = false;
         this.mTooltipExtension = this.mcTooltipHolder.GetExtension(TooltipExtension) as TooltipExtension;
         if(this.btnIncrease)
         {
            this.btnIncrease.addEventListener(PushButtonEvent.CLICK,this.OnIncreaseClick,false,0,true);
         }
         if(this.btnDecrease)
         {
            this.btnDecrease.addEventListener(PushButtonEvent.CLICK,this.OnDecreaseClick,false,0,true);
         }
         this.addEventListener(MouseEvent.ROLL_OUT,this.OnMouseRollOut,false,0,true);
         this.addEventListener(MouseEvent.ROLL_OVER,this.OnMouseRollOver,false,0,true);
         this.mcPriceStrikeThrough = new Sprite();
         this.mcPriceStrikeThrough.x = this.mcBackgroundMiddle.x;
         this.mcPriceStrikeThrough.y = this.mcBackgroundMiddle.y;
         addChild(this.mcPriceStrikeThrough);
         if(SystemUtils.UsingConsoleInputMode)
         {
            this.InitGamepad();
         }
         this.A11yHookSpinButtons();
      }
      
      override public function Draw(param1:Object, param2:Object = null) : void
      {
         var _loc3_:PurchasePickerRowData = null;
         var _loc7_:TextField = null;
         var _loc11_:int = 0;
         super.Draw(param1,param2);
         _loc3_ = param1 as PurchasePickerRowData;
         var _loc4_:CatalogProduct = _loc3_.CatalogProductDefinition;
         if(!_loc4_)
         {
            return;
         }
         if(_loc3_.showCost)
         {
            (this.mcNumAvailableBackground.GetExtension(TooltipExtension) as TooltipExtension).SetText(KeysGP.PURCHASE_PICKER_AVAILABLE_TOOLTIP);
         }
         if(this.btnIncrease)
         {
            this.btnIncrease.removeEventListener(PushButtonEvent.CLICK,this.OnIncreaseClick,false);
         }
         if(this.btnDecrease)
         {
            this.btnDecrease.removeEventListener(PushButtonEvent.CLICK,this.OnDecreaseClick,false);
         }
         var _loc5_:Boolean = _loc3_.enableRow && _loc3_.base_data.is_enable;
         this.gotoAndStop(_loc5_ ? "up" : "disabled");
         this.txtItemAmount = this.mcNumContainer.txtItemAmount;
         this.mcItemAmountBackground = this.mcNumContainer.mcItemAmountBackground;
         this.btnIncrease = this.mcNumContainer.btnIncrease;
         this.btnDecrease = this.mcNumContainer.btnDecrease;
         if(this.btnIncrease)
         {
            this.btnIncrease.addEventListener(PushButtonEvent.CLICK,this.OnIncreaseClick,false,0,true);
         }
         if(this.btnDecrease)
         {
            this.btnDecrease.addEventListener(PushButtonEvent.CLICK,this.OnDecreaseClick,false,0,true);
         }
         this.A11yHookSpinButtons();
         this.txtItemAmount.htmlText = KeysGP.PURCHASE_PICKER_ITEM_AMOUNT.toString(_loc3_.purchaseAmount);
         this.mMaxTunedSelectable = _loc3_.maxSelectableInRow;
         var _loc6_:int = _loc3_.num_available;
         this.mNumAvailable = _loc6_;
         if(_loc6_ >= 0)
         {
            this.txtNumAvailable.visible = true;
            this.mcNumAvailableBackground.visible = true;
            this.txtNumAvailable.htmlText = _loc6_ <= 99 ? Keys.GENERIC_NUMBER.toString(_loc6_) : KeysGP.INVENTORY_ABOVE_NINETY_NINE.toString();
            this.mcNumAvailableBackground.gotoAndStop("normal");
         }
         else
         {
            this.txtNumAvailable.visible = false;
            this.mcNumAvailableBackground.visible = false;
         }
         this.CheckItemAmount(_loc3_.purchaseAmount);
         if(Boolean(!_loc5_) && Boolean(this.btnIncrease) && Boolean(this.btnDecrease))
         {
            this.btnIncrease.enabled = false;
            this.btnDecrease.enabled = false;
         }
         if(!_loc3_.mEnableIncrease && Boolean(this.btnIncrease))
         {
            this.btnIncrease.enabled = false;
         }
         this.mcBackgroundMiddle.visible = this.txtCost.visible = _loc3_.showCost;
         this.mcBackgroundLeft.width = _loc3_.nameColumnWidth;
         _loc7_ = this.txtNumOwned;
         var _loc8_:MovieClip = this.mcItemAmountBackground;
         _loc7_.htmlText = KeysGP.PURCHASE_PICKER_NUM_OWNED.toString(_loc3_.num_owned);
         if(_loc3_.num_owned > 0)
         {
            _loc7_.visible = true;
            this.mcNumContainer.y = (this.height - this.mcNumContainer.height - _loc7_.height - PurchasePickerTunables.MARGIN_BETWEEN_BUY_COMPONENT_AND_NUM_OWNED) / 2;
         }
         else
         {
            _loc7_.visible = false;
            this.mcNumContainer.y = (this.height - this.mcNumContainer.height) / 2;
         }
         _loc7_.y = _loc7_.visible ? this.mcNumContainer.y + this.mcNumContainer.height + _loc7_.height / 2 + PurchasePickerTunables.MARGIN_BETWEEN_BUY_COMPONENT_AND_NUM_OWNED : 0;
         TextUtils.SetAndEllipsizeText(this.txtName,_loc4_.Name);
         if(_loc3_.is_discounted && _loc3_.custom_price != -1)
         {
            this.txtCost.autoSize = TextFieldAutoSize.CENTER;
            this.txtCost.multiline = true;
            this.mcPriceStrikeThrough.visible = true;
            _loc11_ = _loc3_.prediscounted_price == -1 ? int(_loc4_.price) : _loc3_.prediscounted_price;
            TextUtils.FormatDiscountedTextfieldWithStrikeThrough(this.txtCost,KeysGP.GRID_PICKER_DISCOUNTED_PRICE.toString(_loc11_,_loc3_.custom_price),PickersTunables.DISCOUNTED_PRICE_COLOR,this.mcPriceStrikeThrough);
         }
         else
         {
            this.txtCost.multiline = false;
            this.mcPriceStrikeThrough.visible = false;
            this.txtCost.htmlText = GameplayStateData.CurrentRegionCurrencyStringKey.toString(_loc3_.custom_price == -1 ? _loc4_.price : _loc3_.custom_price);
         }
         if(_loc3_.base_data.icon_info)
         {
            ImageUtils.LoadFromIconInfo(this.mcIcon,_loc3_.base_data.icon_info,ImageUtils.THUMBNAIL_SIZE_MEDIUM);
         }
         else
         {
            ImageUtils.LoadObjectThumbnail(this.mcIcon,_loc3_.def_id,ImageUtils.THUMBNAIL_SIZE_MEDIUM);
         }
         var _loc9_:LocKey = _loc3_.base_data.description;
         var _loc10_:String = _loc9_ != null && _loc9_.IsValid() ? _loc9_.toString() : _loc4_.Description;
         TextUtils.SetAndEllipsizeText(this.txtDescription,_loc10_);
         this.txtDescription.visible = _loc3_.showDescription;
         this.txtDescription.y = this.txtName.y + this.txtName.textHeight + PurchasePickerTunables.MARGIN_BETWEEN_TITLE_AND_DESCRIPTION_IN_CELL;
         this.mTooltipExtension.Data = _loc3_.showDescriptionTooltip ? {
            "type":Tooltip.TYPE_TITLE_DESCRIPTION,
            "title":_loc4_.Name,
            "text":_loc4_.Description
         } : null;
      }
      
      public function IncreaseAmount() : void
      {
         if(Boolean(this.btnIncrease) && !this.btnIncrease.enabled)
         {
            return;
         }
         if(this.mNumAvailable == 0)
         {
            this.mcNumAvailableBackground.gotoAndPlay("zero_animation");
         }
         this.dispatchEvent(new Event(PurchasePicker.INCREASE_AMOUNT_EVENT));
         this.A11yQueueAmountAnnounce();
      }

      public function DecreaseAmount() : void
      {
         if(!this.btnDecrease.enabled)
         {
            return;
         }
         this.dispatchEvent(new Event(PurchasePicker.DECREASE_AMOUNT_EVENT));
         this.A11yQueueAmountAnnounce();
      }

      // a11y (Screen Reader mod): the quantity spinner and cart totals were
      // silent, which fails the basic accessible-cart contract (announce the
      // new value on change; announce totals politely after changes; give
      // the +/- buttons the item's name for context). IncreaseAmount /
      // DecreaseAmount are the single funnel for mouse AND gamepad, so the
      // announce hook lives there. The new value is read one frame later:
      // the click dispatches an event the picker handles by redrawing this
      // cell, so txtItemAmount is stale at dispatch time. Totals are read
      // off the picker's own ALREADY-LOCALIZED footer fields and announced
      // on the non-interrupting event channel after a 1.2 s lull.
      protected var mA11yFrameArmed:Boolean = false;

      protected var mA11yTotalsTimer:Timer;

      public function A11yPost(param1:String, param2:String) : void
      {
         var _loc3_:String = null;
         try
         {
            if(param2 == null || param2.length == 0)
            {
               return;
            }
            _loc3_ = encodeURIComponent(param2);
            _loc3_ = _loc3_.split("'").join("%27");
            _loc3_ = _loc3_.split("(").join("%28");
            _loc3_ = _loc3_.split(")").join("%29");
            _loc3_ = _loc3_.split("!").join("%21");
            _loc3_ = _loc3_.split("~").join("%7E");
            _loc3_ = _loc3_.split("*").join("%2A");
            CommunicationManager.PostServerCommand(param1,_loc3_);
         }
         catch(e:Error)
         {
         }
      }

      public function A11yQueueAmountAnnounce() : void
      {
         try
         {
            if(!this.mA11yFrameArmed)
            {
               this.mA11yFrameArmed = true;
               addEventListener(Event.ENTER_FRAME,this.A11yOnAmountFrame,false,0,true);
            }
            if(this.mA11yTotalsTimer == null)
            {
               this.mA11yTotalsTimer = new Timer(1200,1);
               this.mA11yTotalsTimer.addEventListener(TimerEvent.TIMER_COMPLETE,this.A11yOnTotalsTimer,false,0,true);
            }
            this.mA11yTotalsTimer.reset();
            this.mA11yTotalsTimer.start();
         }
         catch(e:Error)
         {
         }
      }

      public function A11yOnAmountFrame(param1:Event) : void
      {
         try
         {
            removeEventListener(Event.ENTER_FRAME,this.A11yOnAmountFrame);
            this.mA11yFrameArmed = false;
            this.A11yPost("a11y.widget_enc",this.txtItemAmount.text);
         }
         catch(e:Error)
         {
         }
      }

      public function A11yFindPicker() : Object
      {
         var _loc1_:DisplayObject = this;
         var _loc2_:int = 0;
         var _loc3_:Object = null;
         while(_loc1_ != null && _loc2_ < 14)
         {
            try
            {
               _loc3_ = _loc1_;
               if(_loc3_["txtItemCount"] != null && _loc3_["txtCost"] != null)
               {
                  return _loc3_;
               }
            }
            catch(e:Error)
            {
            }
            _loc1_ = _loc1_.parent;
            _loc2_++;
         }
         return null;
      }

      public function A11yOnTotalsTimer(param1:TimerEvent) : void
      {
         var _loc2_:Object = null;
         var _loc3_:String = null;
         try
         {
            _loc2_ = this.A11yFindPicker();
            if(_loc2_ == null)
            {
               return;
            }
            // EA's own footer labels and values, so every language is free:
            // "Total Count: 4" + "Total Cost: §100".
            _loc3_ = "";
            try
            {
               _loc3_ = _loc2_["txtTotalItemsLabel"]["text"] + " " + _loc2_["txtItemCount"]["text"];
            }
            catch(e1:Error)
            {
            }
            try
            {
               _loc3_ += "" + _loc2_["txtTotalCostLabel"]["text"] + " " + _loc2_["txtCost"]["text"];
            }
            catch(e2:Error)
            {
            }
            this.A11yPost("a11y.event_enc",_loc3_);
         }
         catch(e:Error)
         {
         }
      }

      public function A11yOnIncreaseOver(param1:MouseEvent) : void
      {
         this.A11yAnnounceSpin("increase");
      }

      public function A11yOnDecreaseOver(param1:MouseEvent) : void
      {
         this.A11yAnnounceSpin("decrease");
      }

      public function A11yAnnounceSpin(param1:String) : void
      {
         var _loc2_:String = null;
         try
         {
            // Token first ("increase"/"decrease", localized Python-side like
            // checked/unchecked), then the item name for context, then the
            // current quantity: the accessible name-in-context pattern.
            _loc2_ = param1 + "" + this.txtName.text + "" + this.txtItemAmount.text;
            this.A11yPost("a11y.widget_enc",_loc2_);
         }
         catch(e:Error)
         {
         }
      }

      public function A11yHookSpinButtons() : void
      {
         try
         {
            if(this.btnIncrease)
            {
               this.btnIncrease.addEventListener(MouseEvent.ROLL_OVER,this.A11yOnIncreaseOver,false,0,true);
            }
            if(this.btnDecrease)
            {
               this.btnDecrease.addEventListener(MouseEvent.ROLL_OVER,this.A11yOnDecreaseOver,false,0,true);
            }
         }
         catch(e:Error)
         {
         }
      }
      
      protected function OnIncreaseClick(param1:PushButtonEvent) : void
      {
         this.IncreaseAmount();
      }
      
      protected function OnDecreaseClick(param1:PushButtonEvent) : void
      {
         this.DecreaseAmount();
      }
      
      protected function OnMouseRollOver(param1:MouseEvent) : void
      {
         gotoAndPlay("over");
         this.dispatchEvent(new GUIEvent(GUIEvent.REDRAW));
      }
      
      protected function OnMouseRollOut(param1:MouseEvent) : void
      {
         gotoAndPlay("up");
         this.dispatchEvent(new GUIEvent(GUIEvent.REDRAW));
      }
      
      protected function CheckItemAmount(param1:uint) : void
      {
         var _loc2_:uint = PurchasePicker.MAX_AMOUNT_PER_ITEM;
         if(this.mMaxTunedSelectable > 0)
         {
            _loc2_ = this.mMaxTunedSelectable;
         }
         if(this.btnIncrease)
         {
            this.btnIncrease.enabled = param1 < _loc2_ && this.mNumAvailable != 0;
         }
         if(this.btnDecrease)
         {
            this.btnDecrease.enabled = param1 > 0;
         }
      }
      
      protected function InitGamepad() : void
      {
         this.addEventListener(HighlightRequestEvent.HIGHLIGHT_REQUEST,this.HandleHighlightRequest,false,0,true);
      }
      
      protected function HandleHighlightRequest(param1:HighlightRequestEvent) : void
      {
         var _loc2_:TooltipExtension = this.mcTooltipHolder.GetExtension(TooltipExtension,false) as TooltipExtension;
         if(!_loc2_)
         {
            return;
         }
         if(param1.shouldHighlight)
         {
            _loc2_.Show();
         }
         else
         {
            _loc2_.Clear();
         }
      }
      
      internal function frame10() : *
      {
         stop();
      }
      
      internal function frame20() : *
      {
         stop();
      }
      
      internal function frame30() : *
      {
         stop();
      }
      
      internal function frame40() : *
      {
         stop();
      }
   }
}

