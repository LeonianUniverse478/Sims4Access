package widgets.Pickers
{
   import flash.display.DisplayObject;
   import gamedata.Gameplay.Pickers.UiDialogPicker;
   import olympus.core.TooltipManager;
   import widgets.Pickers.controls.FashionPurchasePicker.FashionPurchasePicker;
   import widgets.Pickers.controls.PurchasePicker.PurchasePicker;
   import widgets.Pickers.controls.RewardsPicker.RewardsPicker;
   
   public class PickersPurchaseMain extends PickersMainBase
   {
      
      public function PickersPurchaseMain()
      {
         super();
      }
      
      override protected function SetPicker(param1:int) : void
      {
         switch(param1)
         {
            case UiDialogPicker.OBJECTPICKERTYPE_PURCHASE:
            case UiDialogPicker.OBJECTPICKERTYPE_SELL:
               if(!mPicker || mPicker is FashionPurchasePicker || !(mPicker is PurchasePicker))
               {
                  mPicker = new PurchasePicker();
                  mPicker.Initialize();
               }
               break;
            case UiDialogPicker.OBJECTPICKERTYPE_FASHION_PURCHASE:
               if(!mPicker || !(mPicker is FashionPurchasePicker))
               {
                  mPicker = new FashionPurchasePicker();
                  mPicker.Initialize();
               }
               break;
            case UiDialogPicker.OBJECTPICKERTYPE_BUSINESS_PERKS:
            case UiDialogPicker.OBJECTPICKERTYPE_SATISFACTION_REWARDS:
               if(!mPicker || !(mPicker is RewardsPicker))
               {
                  mPicker = new RewardsPicker();
                  mPicker.Initialize();
               }
               break;
            default:
               mPicker = null;
         }
         this.A11yFocusPicker();
      }

      // a11y: keyboard navigation never engaged in the purchase picker
      // (tester: "doesn't allow scrolling through the options via keyboard
      // like previous dialogs/pickers"). Our A11yFocusInto hook lives in
      // widgets.Pickers.PickersMain, which is defined ONLY in the Pickers
      // movie; the purchase picker is a different movie and class, so no
      // focus scope was ever set and Numpad 6/4 had nothing to walk.
      //
      // Hooked HERE and not in PickersMainBase.Show on purpose:
      // PickersMainBase is defined in SEVEN movies (PickersColumnBased,
      // Food, Grid, Multi, Outfit, Purchase, Sim), so patching it would be
      // an app-domain lottery: only the first-loaded copy runs (the
      // CommodityContainer lesson). PickersPurchaseMain is defined in
      // exactly one movie. SetPicker runs from Show() on open, and the
      // silent-preload path returns before reaching it, so a hidden
      // preload never steals focus. A11yFocusInto retries for ~24 frames,
      // so being called before the rows exist is fine and expected.
      public function A11yFocusPicker() : void
      {
         var _loc1_:DisplayObject = null;
         try
         {
            // Scope to the PICKER, not to this widget. PickersMainBase
            // never addChild()s mPicker; it just hands the reference to
            // the game via the PickerSet message, so the rows are NOT
            // descendants of this widget. (widgets.Pickers.PickersMain,
            // which our other picker hook uses, DOES parent its picker,
            // which is why scoping to `this` works there and not here.)
            // Scoping to the widget found zero focusables, so A11yTabMove
            // fell back to the whole stage and focus landed on the outer
            // UI instead of the picker rows.
            //
            // The picker is not on stage or populated yet at this point;
            // A11yFocusInto polls until it is (it waits for stage != null
            // AND at least one focusable), so the rows only need to exist
            // within the retry budget.
            _loc1_ = mPicker as DisplayObject;
            if(_loc1_ == null)
            {
               _loc1_ = this;
            }
            TooltipManager.getInstance().A11yFocusInto(_loc1_);
         }
         catch(e:Error)
         {
         }
      }
   }
}

