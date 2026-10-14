package widgets.Pickers
{
   import flash.display.MovieClip;
   import flash.geom.Point;
   import gamedata.Dialog.UiDialogMessage;
   import gamedata.Gameplay.Pickers.UiDialogMultiPickerItem;
   import gamedata.Gameplay.Pickers.UiDialogPicker;
   import olympus.constants.WindowAnimation;
   import olympus.controls.IconComponent;
   import olympus.core.widget.WidgetBase;
   import olympus.events.GenericEvent;
   import olympus.extensions.TutorialTipExtension;
   import olympus.gamepad.EnterParams;
   import olympus.gamepad.NavManager;
   import olympus.input.IInputFocusable;
   import olympus.input.adapters.InputAdapterEvent;
   import olympus.core.TooltipManager;
   import olympus.io.CommunicationManager;
   import olympus.utils.DisplayObjectUtils;
   import olympus.utils.ImageUtils;
   import olympus.utils.SystemUtils;
   import widgets.Pickers.constants.PickersTunables;
   import widgets.Pickers.controls.GUIPicker;
   import widgets.Pickers.controls.PickerBase;
   import widgets.shared.constants.TutorialTipUIElement;
   
   public class PickersMain extends WidgetBase
   {
      
      public var mcOwnerIcon:IconComponent;
      
      public var mcMask:MovieClip;
      
      public var mcOwnerIconBackground:MovieClip;
      
      protected var mPicker:PickerBase;
      
      protected var mPickerSize:Point;
      
      protected var mAudioContext:String;
      
      protected var mDialogMsg:UiDialogMessage;
      
      protected var mPickerData:UiDialogPicker;
      
      protected var mTutorialControlEnum:String;
      
      protected var mPendingSubPickerLoads:Array;
      
      protected var mCachedPickerSetArgs:Object;
      
      protected var mLoadedPickerWidgets:Array = new Array();
      
      public function PickersMain()
      {
         super();
         mAudioExtension.Context = "Default";
      }

      public function A11ySingleSelection() : Boolean
      {
         return this.mDialogMsg != null && this.mPickerData != null &&
            this.mDialogMsg.dialog_type != UiDialogMessage.TYPE_OBJECT_MULTI_PICKER &&
            this.mDialogMsg.dialog_type != UiDialogMessage.TYPE_CUSTOMIZE_OBJECT_MULTI_PICKER &&
            this.mPickerData.max_selectable == 1;
      }
      
      override public function Initialize() : void
      {
         super.Initialize();
         Telemetry.EnableVisibilityTelemetry = false;
         this.visible = true;
      }
      
      override public function Unload() : void
      {
         var _loc1_:WidgetBase = null;
         if(this.mLoadedPickerWidgets.length > 0)
         {
            for each(_loc1_ in this.mLoadedPickerWidgets)
            {
               _loc1_.Unload();
            }
            this.mLoadedPickerWidgets.length = 0;
         }
         else if(Boolean(this.mPicker) && !this.mPicker.HasBeenHidden())
         {
            this.mPicker.Hide(new Array());
         }
         super.Unload();
      }
      
      override public function set visible(param1:Boolean) : void
      {
         super.visible = param1;
         TutorialTipExtension.Get(this).MarkVisibility(super.visible);
      }
      
      override public function Show(param1:Object = null) : void
      {
         var _loc3_:int = 0;
         var _loc4_:String = null;
         var _loc5_:Array = null;
         var _loc6_:Array = null;
         var _loc7_:UiDialogMultiPickerItem = null;
         var _loc8_:int = 0;
         var _loc9_:String = null;
         var _loc10_:String = null;
         this.mDialogMsg = param1 as UiDialogMessage;
         this.mPickerData = this.mDialogMsg.picker_data;
         TooltipManager.getInstance().A11yFocusInto(this);
         this.mcOwnerIcon.visible = this.mcOwnerIconBackground.visible = this.mcMask.visible = false;
         var _loc2_:PickerBase = this.mPicker;
         if(_loc2_)
         {
            removeChild(_loc2_);
            if(visible)
            {
               CommunicationManager.SendUIMessage("HidePickers",null);
            }
         }
         this.mTutorialControlEnum = TutorialTipUIElement.UI_INVALID;
         this.mPendingSubPickerLoads = null;
         if(this.mDialogMsg.dialog_type == UiDialogMessage.TYPE_OBJECT_MULTI_PICKER || this.mDialogMsg.dialog_type == UiDialogMessage.TYPE_CUSTOMIZE_OBJECT_MULTI_PICKER)
         {
            _loc3_ = int(this.mDialogMsg.dialog_type);
            _loc4_ = "PickersMulti";
            _loc5_ = new Array();
            _loc6_ = this.mDialogMsg.multi_picker_data.multi_picker_items;
            for each(_loc7_ in _loc6_)
            {
               _loc8_ = UiDialogPicker.RemapPickerPerkType(_loc7_.picker_data.type);
               _loc9_ = this.GetPickerWidgetNameForType(_loc8_);
               if((Boolean(_loc9_)) && _loc5_.indexOf(_loc9_) == -1)
               {
                  _loc5_.push(_loc9_);
               }
            }
            if(_loc5_.length > 0)
            {
               this.mPendingSubPickerLoads = _loc5_;
               AddMessageListener("SilentPickerSet",this.OnSilentPickerSet);
               for each(_loc10_ in _loc5_)
               {
                  CommunicationManager.SendMessage("Show" + _loc10_,{"loadSilently":true});
               }
            }
         }
         else
         {
            if(Boolean(this.mDialogMsg.text) && this.mDialogMsg.text.IsValid())
            {
               this.mPickerData.subtitle = this.mDialogMsg.text;
            }
            _loc3_ = UiDialogPicker.RemapPickerPerkType(this.mPickerData.type);
            _loc4_ = this.GetPickerWidgetNameForType(_loc3_);
            if(!_loc4_)
            {
               switch(_loc3_)
               {
                  case UiDialogPicker.OBJECTPICKERTYPE_LOT:
                  case UiDialogPicker.OBJECTPICKERTYPE_OBJECT:
                  case UiDialogPicker.OBJECTPICKERTYPE_OBJECT_LARGE:
                  case UiDialogPicker.OBJECTPICKERTYPE_OBJECT_SQUARE:
                  case UiDialogPicker.OBJECTPICKERTYPE_ITEM:
                  case UiDialogPicker.OBJECTPICKERTYPE_LARGE_TEXT_FLAIR:
                  case UiDialogPicker.OBJECTPICKERTYPE_OBJECT_TEXT:
                  case UiDialogPicker.OBJECTPICKERTYPE_OBJECT_TEXT_ADD:
                  case UiDialogPicker.OBJECTPICKERTYPE_RELATIONSHIP:
                  case UiDialogPicker.OBJECTPICKERTYPE_OBJECT_EXPANDED_INFO:
                  case UiDialogPicker.OBJECTPICKERTYPE_OBJECT_CAS_ICON:
                  case UiDialogPicker.OBJECTPICKERTYPE_OBJECT_ICON_TITLE:
                     if(_loc2_ is GUIPicker)
                     {
                        break;
                     }
                     _loc2_ = new GUIPicker();
               }
               if(_loc2_)
               {
               }
            }
            else if(_loc4_ == "PickersSim")
            {
               this.mTutorialControlEnum = TutorialTipUIElement.LIVE_SIM_PICKER_UI;
            }
         }
         if(_loc4_)
         {
            AddMessageListener("PickerSet",this.OnPickerSet);
            CommunicationManager.SendMessage("Show" + _loc4_,{"pickerType":_loc3_});
         }
         else
         {
            this.OnPickerSet({
               "picker":_loc2_,
               "widget":null
            });
         }
      }
      
      protected function OnPickerSet(param1:Object) : void
      {
         var _loc2_:PickerBase = null;
         CommunicationManager.RemoveMessageListener("PickerSet",this.OnPickerSet,this);
         if(Boolean(this.mPendingSubPickerLoads) && this.mPendingSubPickerLoads.length > 0)
         {
            this.mCachedPickerSetArgs = param1;
            return;
         }
         _loc2_ = param1["picker"];
         if(!_loc2_)
         {
            return;
         }
         var _loc3_:WidgetBase = param1["widget"];
         if(_loc3_)
         {
            this.mLoadedPickerWidgets.push(_loc3_);
         }
         TutorialTipExtension.Get(this).ControlEnum = this.mTutorialControlEnum;
         super.Show(this.mDialogMsg);
         if(this.mDialogMsg.background_audio_event)
         {
            this.mAudioContext = this.mDialogMsg.background_audio_event;
            mAudioExtension.DispatchShow(this.mAudioContext);
         }
         else
         {
            this.mAudioContext = null;
         }
         addChildAt(_loc2_,0);
         _loc2_.Show(this.mDialogMsg);
         if(SystemUtils.UsingConsoleInputMode && !_loc2_.ShouldDisableCloseButton())
         {
            _loc2_.OnInputEventCall(InputAdapterEvent.BACK,this.HandleBackInput);
         }
         var _loc4_:Point = _loc2_.GetPickerSize();
         if(_loc4_)
         {
            _loc2_.x = -_loc4_.x * 0.5;
            _loc2_.y = -_loc4_.y * 0.5;
         }
         this.mPicker = _loc2_;
         try { TooltipManager.getInstance().A11yFocusInto(this); }
         catch(a11yError:Error) { }
         this.mPickerSize = _loc4_;
         var _loc5_:IconComponent = this.mcOwnerIcon;
         var _loc6_:String = "0";
         if(this.mPickerData)
         {
            _loc6_ = this.mPickerData.owner_sim_id;
         }
         else if(this.mDialogMsg.override_sim_icon_id != null)
         {
            _loc6_ = this.mDialogMsg.override_sim_icon_id;
         }
         else
         {
            _loc6_ = this.mDialogMsg.owner_id;
         }
         if(Boolean(_loc6_) && _loc6_ != "0")
         {
            _loc5_.visible = true;
            this.mcMask.visible = true;
            this.mcOwnerIconBackground.visible = true;
            this.PositionSimIcon();
            _loc5_.mask = this.mcMask;
            ImageUtils.LoadSimThumbnail(_loc5_,_loc6_,ImageUtils.SIM_THUMBNAIL_TYPE_BUST);
         }
         else
         {
            _loc5_.visible = false;
            this.mcMask.visible = false;
            this.mcOwnerIconBackground.visible = false;
         }
         _loc2_.ownerIconVisible = _loc5_.visible;
         _loc2_.addEventListener(GenericEvent.RESIZE,this.OnPickerResized);
         var _loc7_:int = AnimateIn(0,WindowAnimation.WINDOW_LARGE_HORIZONTAL_IN);
         DisplayObjectUtils.CreateInputBlocker(this,_loc7_);
         if(SystemUtils.UsingController)
         {
            if(CommunicationManager.CallUIService("IsTransitionScreenVisible"))
            {
               CommunicationManager.SendUIMessage("HidePickers");
               return;
            }
            while(NavManager.Instance.CurrentWidget == this)
            {
               NavManager.Instance.FocusBack();
            }
            NavManager.Instance.FocusWidgetForward(WidgetName,null,null,false,this.mPickerData ? this.mPickerData.mbFromDialog : false);
         }
         if(SystemUtils.UsingMouseKeyboard)
         {
            AddMessageListener("UsingControllerToggled",this.HandleUsingControllerToggled);
            AddMessageListener("PostUsingControllerToggled",this.HandlePostUsingControllerToggled);
         }
      }
      
      protected function OnSilentPickerSet(param1:Object) : void
      {
         var _loc2_:WidgetBase = param1["widget"];
         if(_loc2_)
         {
            this.mLoadedPickerWidgets.push(_loc2_);
         }
         var _loc3_:int = this.mPendingSubPickerLoads.indexOf(_loc2_.WidgetName);
         if(_loc3_ != -1)
         {
            this.mPendingSubPickerLoads.splice(_loc3_,1);
         }
         if(this.mPendingSubPickerLoads.length == 0 && Boolean(this.mCachedPickerSetArgs))
         {
            this.mPendingSubPickerLoads = null;
            this.OnPickerSet(this.mCachedPickerSetArgs);
            this.mCachedPickerSetArgs = null;
         }
      }
      
      override public function Hide(param1:Object = null) : void
      {
         var _loc2_:WidgetBase = null;
         if(this.mLoadedPickerWidgets.length > 0)
         {
            for each(_loc2_ in this.mLoadedPickerWidgets)
            {
               _loc2_.Hide(param1);
            }
            this.mLoadedPickerWidgets.length = 0;
         }
         else if(Boolean(this.mPicker) && !this.mPicker.HasBeenHidden())
         {
            this.mPicker.Hide(new Array());
         }
         if(SystemUtils.UsingController)
         {
            while(NavManager.Instance.CurrentWidget == this)
            {
               NavManager.Instance.FocusBack();
            }
         }
         super.Hide(param1);
         if(this.mAudioContext)
         {
            mAudioExtension.DispatchHide(this.mAudioContext);
            this.mAudioContext = null;
         }
      }
      
      override public function HandleRequestHide(param1:Object) : Object
      {
         if(this.mPicker.ShouldDisableCloseButton())
         {
            return true;
         }
         return super.HandleRequestHide(param1);
      }
      
      override public function HandleStageResized(param1:Number, param2:Number) : void
      {
         if(this.mPicker)
         {
            this.mPicker.HandleStageResized(param1,param2);
            this.CenterPicker();
         }
      }
      
      protected function OnPickerResized(param1:GenericEvent) : void
      {
         if(param1.data)
         {
            this.mPickerSize = param1.data as Point;
         }
         else
         {
            this.mPickerSize = this.mPicker.GetPickerSize();
         }
         this.CenterPicker();
         this.PositionSimIcon();
      }
      
      protected function PositionSimIcon() : void
      {
         var _loc1_:IconComponent = this.mcOwnerIcon;
         _loc1_.x = this.mPicker.x - PickersTunables.SIM_THUMBNAIL_SIZE.x * PickersTunables.SIM_THUMBNAIL_PERCENT_OFFSET.x;
         _loc1_.y = this.mPicker.y - PickersTunables.SIM_THUMBNAIL_SIZE.y * PickersTunables.SIM_THUMBNAIL_PERCENT_OFFSET.y;
         this.mcOwnerIconBackground.x = _loc1_.x;
         this.mcOwnerIconBackground.y = _loc1_.y + PickersTunables.SIM_THUMBNAIL_BACKGROUND_OFFSET.y;
         this.mcMask.x = _loc1_.x;
         this.mcMask.y = _loc1_.y + PickersTunables.SIM_THUMBNAIL_BACKGROUND_OFFSET.y;
      }
      
      protected function CenterPicker() : void
      {
         if(this.mPickerSize)
         {
            this.mPicker.x = -this.mPickerSize.x * 0.5;
            this.mPicker.y = -this.mPickerSize.y * 0.5;
         }
      }
      
      protected function GetPickerWidgetNameForType(param1:int) : String
      {
         switch(param1)
         {
            case UiDialogPicker.OBJECTPICKERTYPE_SIM:
            case UiDialogPicker.OBJECTPICKERTYPE_SIM_SITUATION:
            case UiDialogPicker.OBJECTPICKERTYPE_SIM_TRAVEL:
            case UiDialogPicker.OBJECTPICKERTYPE_SIM_TRAVEL_LIVE:
            case UiDialogPicker.OBJECTPICKERTYPE_SIM_CLUB:
               return "PickersSim";
            case UiDialogPicker.OBJECTPICKERTYPE_RECIPE:
               return "PickersGrid";
            case UiDialogPicker.OBJECTPICKERTYPE_BUSINESS_PERKS:
            case UiDialogPicker.OBJECTPICKERTYPE_SATISFACTION_REWARDS:
            case UiDialogPicker.OBJECTPICKERTYPE_PURCHASE:
            case UiDialogPicker.OBJECTPICKERTYPE_FASHION_PURCHASE:
            case UiDialogPicker.OBJECTPICKERTYPE_SELL:
               return "PickersPurchase";
            case UiDialogPicker.OBJECTPICKERTYPE_LOT:
            case UiDialogPicker.OBJECTPICKERTYPE_OBJECT:
            case UiDialogPicker.OBJECTPICKERTYPE_OBJECT_LARGE:
            case UiDialogPicker.OBJECTPICKERTYPE_OBJECT_SQUARE:
            case UiDialogPicker.OBJECTPICKERTYPE_ITEM:
            case UiDialogPicker.OBJECTPICKERTYPE_LARGE_TEXT_FLAIR:
            case UiDialogPicker.OBJECTPICKERTYPE_OBJECT_TEXT:
            case UiDialogPicker.OBJECTPICKERTYPE_RELATIONSHIP:
            case UiDialogPicker.OBJECTPICKERTYPE_OBJECT_EXPANDED_INFO:
            case UiDialogPicker.OBJECTPICKERTYPE_OBJECT_TEXT_ADD:
            case UiDialogPicker.OBJECTPICKERTYPE_OBJECT_CAS_ICON:
            case UiDialogPicker.OBJECTPICKERTYPE_OBJECT_ICON_TITLE:
               break;
            case UiDialogPicker.OBJECTPICKERTYPE_OUTFIT:
            case UiDialogPicker.OBJECTPICKERTYPE_EDIT_OUTFIT:
               return "PickersOutfit";
            case UiDialogPicker.OBJECTPICKERTYPE_FOOD:
               return "PickersFood";
            case UiDialogPicker.OBJECTPICKERTYPE_ODD_JOBS:
            case UiDialogPicker.OBJECTPICKERTYPE_QUESTS:
            case UiDialogPicker.OBJECTPICKERTYPE_MISSIONS:
               return "PickersColumnBased";
         }
         return null;
      }
      
      protected function HandleBackInput() : void
      {
         CommunicationManager.SendUIMessage("HidePickers",null);
      }
      
      override public function Enter(param1:EnterParams = null) : IInputFocusable
      {
         return this.mPicker.Enter(param1);
      }
      
      override public function OnExited() : void
      {
         this.mPicker.Exit();
      }
      
      protected function HandleUsingControllerToggled() : void
      {
         if(this.mPicker)
         {
            this.mPicker.HandleUsingControllerToggled();
         }
      }
      
      protected function HandlePostUsingControllerToggled() : void
      {
         if(this.mPicker)
         {
            this.mPicker.HandlePostUsingControllerToggled();
         }
      }
   }
}

