package widgets.Gameplay.AgeUpPanel
{
   import flash.display.DisplayObject;
   import flash.display.MovieClip;
   import flash.events.Event;
   import flash.events.MouseEvent;
   import flash.geom.Point;
   import flash.text.TextField;
   import flash.text.TextFieldAutoSize;
   import gamedata.GameContent;
   import gamedata.Gameplay.AgeUpPanel.SimPersonalityAssignmentDialog;
   import gamedata.Gameplay.Pickers.UiDialogPicker;
   import gamedata.Gameplay.shared.AgeUpdate;
   import gamedata.Gameplay.shared.definitions.AspirationTrackStaticData;
   import gamedata.Gameplay.shared.definitions.TraitsStaticData;
   import gamedata.shared.HouseholdSimData;
   import gamedata.shared.Species;
   import olympus.constants.ActionCodes;
   import olympus.constants.DialogTypes;
   import olympus.controls.IconComponent;
   import olympus.core.Ticker;
   import flash.utils.getDefinitionByName;
   import olympus.core.widget.WidgetBase;
   import olympus.events.GridEvent;
   import olympus.events.IntroOutroAnimEvent;
   import olympus.events.PushButtonEvent;
   import olympus.events.TickerEvent;
   import olympus.extensions.MouseKeyboardVisibilityExtension;
   import olympus.gamepad.EnterParams;
   import olympus.gamepad.LayoutAPI;
   import olympus.gamepad.NavDirection;
   import olympus.gamepad.NavManager;
   import olympus.gui.buttons.Button;
   import olympus.gui.events.GUIEvent;
   import olympus.input.GamepadAnalogSticks;
   import olympus.input.IInputFocusable;
   import olympus.input.InputAction;
   import olympus.input.InputTrigger;
   import olympus.input.adapters.BidirectionalGroupAdapter;
   import olympus.input.adapters.InputAdapterConfirmEvent;
   import olympus.input.adapters.InputAdapterEvent;
   import olympus.input.adapters.InputAdapterLeaveEvent;
   import olympus.input.adapters.OmnidirectionalGroupAdapter;
   import olympus.input.helpers.VirtualKeyboardHelper;
   import olympus.io.CommunicationManager;
   import olympus.io.InputActionManager;
   import olympus.localization.Keys;
   import olympus.localization.KeysConsole;
   import olympus.localization.KeysGP;
   import olympus.localization.LocKey;
   import olympus.utils.DisplayObjectUtils;
   import olympus.utils.ImageUtils;
   import olympus.utils.SystemUtils;
   import olympus.utils.TextUtils;
   import scaleform.clik.controls.TextInput;
   import widgets.Gameplay.AgeUpPanel.constants.AgeUpPanelTunables;
   import widgets.Gameplay.AgeUpPanel.controls.AgeUpInfoPanel;
   import widgets.Gameplay.AgeUpPanel.controls.AgeUpNameInput;
   import widgets.Gameplay.AgeUpPanel.data.AgeUpAspirationSelectionDataFeed;
   import widgets.Gameplay.AgeUpPanel.data.AgeUpTraitsSelectionDataFeed;
   import widgets.TraitsMolecule.TraitSelector;
   import widgets.shared.events.TraitSelectorAspirationEvent;
   import widgets.shared.events.TraitSelectorEvent;
   import widgets.shared.events.TraitSelectorTraitEvent;
   
   public class AgeUpPanelMain extends WidgetBase
   {
      
      public var txtTitle:TextField;
      
      public var txtSubTitle:TextField;
      
      public var btnOk:Button;
      
      public var btnClose:Button;
      
      public var mcBg:MovieClip;
      
      public var mcNamePanel:AgeUpNameInput;
      
      public var mcInfoPanel:AgeUpInfoPanel;
      
      public var mcTraitSelector:TraitSelector;
      
      public var mcReplaceTraitClip:MovieClip;
      
      public var mcBalloons:MovieClip;
      
      public var mcSimImageContainer:MovieClip;
      
      protected var txtReplaceTraitName:TextField;
      
      protected var mcReplaceTraitIcon:IconComponent;
      
      protected var mDialogId:String;
      
      protected var mCurrentDialog:SimPersonalityAssignmentDialog;
      
      protected var mOriginalTraitIds:Array;
      
      protected var mDialogMsgQueue:Vector.<SimPersonalityAssignmentDialog> = new Vector.<SimPersonalityAssignmentDialog>();
      
      protected var mSimId:String;
      
      protected var mTraitMoleculeData:HouseholdSimData = new HouseholdSimData();
      
      protected var mTraitSelectionData:AgeUpTraitsSelectionDataFeed = new AgeUpTraitsSelectionDataFeed();
      
      protected var mAspirationSelectionData:AgeUpAspirationSelectionDataFeed = new AgeUpAspirationSelectionDataFeed();
      
      protected var mOkInputAdapter:BidirectionalGroupAdapter;
      
      protected var mAdoptionInputAdapter:OmnidirectionalGroupAdapter;
      
      protected var mTickerObj:Object = new Object();
      
      protected var mScrollAction:InputAction;
      
      public function AgeUpPanelMain()
      {
         super();
      }
      
      override public function Initialize() : void
      {
         super.Initialize();
         this.txtReplaceTraitName = this.mcReplaceTraitClip.txtReplaceTraitName as TextField;
         this.mcReplaceTraitIcon = this.mcReplaceTraitClip.mcReplaceTraitIcon as IconComponent;
         this.txtTitle.autoSize = TextFieldAutoSize.LEFT;
         this.txtSubTitle.autoSize = TextFieldAutoSize.CENTER;
         this.txtReplaceTraitName.autoSize = TextFieldAutoSize.LEFT;
         var _loc1_:TraitSelector = this.mcTraitSelector;
         _loc1_.addEventListener(TraitSelectorTraitEvent.SELECTED,this.OnTraitsChanged,false,0,true);
         _loc1_.addEventListener(TraitSelectorTraitEvent.REMOVE,this.OnTraitsChanged,false,0,true);
         _loc1_.addEventListener(TraitSelectorAspirationEvent.SELECTED,this.OnTraitsChanged,false,0,true);
         _loc1_.addEventListener(TraitSelectorEvent.OPEN_TRAITS_PANEL,this.OnTraitSelectorPanelOpen,false,0,true);
         _loc1_.addEventListener(TraitSelectorEvent.OPEN_ASPIRATIONS_PANEL,this.OnTraitSelectorPanelOpen,false,0,true);
         _loc1_.mcTraitSelectionPanel.FixedHeight = AgeUpPanelTunables.TRAIT_SELECTION_PANEL_HEIGHT;
         _loc1_.mcAspSelectionPanel.FixedHeight = AgeUpPanelTunables.TRAIT_SELECTION_PANEL_HEIGHT;
         _loc1_.mcTraitSelectionPanel.TitleText = "";
         _loc1_.mcAspSelectionPanel.TitleText = "";
         _loc1_.mcTraitSelectionPanel.DisplayPanelBackground = true;
         _loc1_.mcAspSelectionPanel.DisplayPanelBackground = true;
         _loc1_.mcTraitSelectionPanel.mcTraitList.mSlider.AlwaysVisible = true;
         _loc1_.mcAspSelectionPanel.mcScrollList.mSlider.AlwaysVisible = true;
         _loc1_.HideGhostButton();
         this.mcNamePanel.addEventListener(GUIEvent.REFRESH,this.UpdateOkButton,false,0,true);
         this.btnOk.addEventListener(PushButtonEvent.CLICK,this.OnOkButtonClick,false,0,true);
         this.btnClose.addEventListener(PushButtonEvent.CLICK,this.OnCloseButtonClick,false,0,true);
         addEventListener(MouseEvent.MOUSE_DOWN,this.OnMouseDown,false,0,true);
         if(SystemUtils.UsingConsoleInputMode)
         {
            this.InitializeGamepadInput();
         }
         if(SystemUtils.UsingMouseKeyboard)
         {
            AddMessageListener("UsingControllerToggled",this.HandleUsingControllerToggled);
         }
      }
      
      override public function Show(param1:Object = null) : void
      {
         if(SystemUtils.UsingController)
         {
            Ticker.Add(this.mTickerObj,0,this.Tick);
            InputActionManager.RegisterAction(this.mScrollAction);
            NavManager.Instance.FocusWidgetForward(WidgetName);
         }
         super.Show(param1);
         this.mDialogMsgQueue.push(new SimPersonalityAssignmentDialog(param1));
         if(this.mDialogId == null)
         {
            this.ShowNextDialog();
         }
      }
      
      override public function Hide(param1:Object = null) : void
      {
         TraitsStaticData.ClearStaticDataTraitConflicts();
         super.Hide(param1);
         if(SystemUtils.UsingController)
         {
            Ticker.Remove(this.mTickerObj);
            InputActionManager.UnregisterAction(this.mScrollAction);
            NavManager.Instance.FocusBack();
         }
      }
      
      override public function HandleRequestHide(param1:Object) : Object
      {
         if(this.IsTraitReassignment())
         {
            CommunicationManager.CallGameService("PostServerCommand",{
               "command":"ui.dialog.respond",
               "commandArgs":[this.mDialogId,int(UiDialogPicker.DIALOG_RESPONSE_CLOSED)]
            });
            return super.HandleRequestHide(param1);
         }
         return false;
      }
      
      override public function HandleStageResized(param1:Number, param2:Number) : void
      {
         super.HandleStageResized(param1,param2);
         x = 0.5 * (param1 - this.mcBg.width);
         y = 0.5 * (param2 - this.mcBg.height);
      }
      
      public function A11yFocusPanel() : void
      {
         try { var manager:Object = getDefinitionByName("olympus.core.TooltipManager"); manager["getInstance"]()["A11yFocusInto"](this); }
         catch(e:Error) { }
      }

      public function A11yDismissPanel() : void
      {
         try
         {
            if(this.mcTraitSelector.mcAspSelectionPanel.IsVisible() || (!this.IsTraitReassignment() && this.mcTraitSelector.mcTraitSelectionPanel.IsVisible()))
            {
               this.CloseSubpanels();
            }
            else if(this.IsTraitReassignment()) { this.OnDialogFinished(true); }
         }
         catch(e:Error) { }
      }

      public function CloseSubpanels() : void
      {
         if(this.mcTraitSelector.mcTraitSelectionPanel.IsVisible() && !this.IsTraitReassignment())
         {
            this.mcTraitSelector.SetPanelVisible(this.mcTraitSelector.TraitPanelId,false);
            this.mcTraitSelector.mcTraitSelectionPanel.addEventListener(IntroOutroAnimEvent.FINISH,this.OnTraitSelectorPanelClose,false,0,true);
         }
         else if(this.mcTraitSelector.mcAspSelectionPanel.IsVisible())
         {
            this.mcTraitSelector.SetPanelVisible(this.mcTraitSelector.AspirationPanelId,false);
            this.mcTraitSelector.mcAspSelectionPanel.addEventListener(IntroOutroAnimEvent.FINISH,this.OnTraitSelectorPanelClose,false,0,true);
         }
         this.mcTraitSelector.removeEventListener(TraitSelectorTraitEvent.SELECTED,this.OnTraitSelected);
         this.mcTraitSelector.mcAspSelectionPanel.removeEventListener(TraitSelectorAspirationEvent.SELECTED,this.OnAspirationSelected);
         if(this.mcTraitSelector.ShouldFocusMoleculeOnPanelClose(this.IsTraitReassignment()))
         {
            this.mcTraitSelector.FocusBackToMolecule();
         }
      }
      
      protected function OnOkButtonClick(param1:PushButtonEvent) : void
      {
         if(this.mcNamePanel.visible)
         {
            this.mcNamePanel.Complete();
         }
         else if(this.mcTraitSelector.visible)
         {
            this.FinalizePersonalityAssignments();
         }
         this.OnDialogFinished();
      }
      
      protected function OnCloseButtonClick(param1:PushButtonEvent) : void
      {
         this.OnDialogFinished(true);
      }
      
      protected function OnDialogFinished(param1:Boolean = false) : void
      {
         CommunicationManager.CallGameService("PostServerCommand",{
            "command":"ui.dialog.respond",
            "commandArgs":[this.mDialogId,int(param1 ? UiDialogPicker.DIALOG_RESPONSE_CLOSED : UiDialogPicker.DIALOG_RESPONSE_OK)]
         });
         if(this.mDialogMsgQueue.length == 0)
         {
            this.mDialogId = null;
            this.mCurrentDialog = null;
            CommunicationManager.SendUIMessage("Hide" + WidgetName);
         }
         else
         {
            this.ShowNextDialog();
         }
      }
      
      protected function OnTraitSelectorPanelOpen(param1:TraitSelectorEvent) : void
      {
         this.mcInfoPanel.visible = false;
         this.A11yFocusPanel();
         if(param1.type == TraitSelectorEvent.OPEN_ASPIRATIONS_PANEL)
         {
            this.mcTraitSelector.mcAspSelectionPanel.addEventListener(TraitSelectorAspirationEvent.SELECTED,this.OnAspirationSelected,false,0,true);
         }
         else
         {
            this.mcTraitSelector.addEventListener(TraitSelectorTraitEvent.SELECTED,this.OnTraitSelected,false,0,true);
         }
      }
      
      protected function OnTraitSelectorPanelClose(param1:IntroOutroAnimEvent) : void
      {
         this.A11yFocusPanel();
         if(SystemUtils.UsingController && this.mcTraitSelector.ShouldFocusMoleculeOnPanelClose())
         {
            this.mcTraitSelector.FocusBackToMolecule();
         }
         if(!this.mcTraitSelector.mcAspSelectionPanel.visible && !this.mcTraitSelector.mcTraitSelectionPanel.visible)
         {
            this.mcInfoPanel.visible = true;
         }
         this.mcTraitSelector.mcAspSelectionPanel.removeEventListener(IntroOutroAnimEvent.FINISH,this.OnTraitSelectorPanelClose);
         this.mcTraitSelector.mcTraitSelectionPanel.removeEventListener(IntroOutroAnimEvent.FINISH,this.OnTraitSelectorPanelClose);
      }
      
      protected function OnTraitSelected(param1:TraitSelectorTraitEvent) : void
      {
         if(!this.IsTraitReassignment())
         {
            this.mcTraitSelector.SetPanelVisible(this.mcTraitSelector.TraitPanelId,false);
            this.mcTraitSelector.mcTraitSelectionPanel.addEventListener(IntroOutroAnimEvent.FINISH,this.OnTraitSelectorPanelClose,false,0,true);
            this.mcTraitSelector.HideGhostButton();
         }
      }
      
      protected function OnAspirationSelected(param1:TraitSelectorAspirationEvent) : void
      {
         this.mcTraitSelector.SelectAspiration(param1.mAspirationId);
         this.mcTraitSelector.SetPanelVisible(this.mcTraitSelector.AspirationPanelId,false);
         this.mcTraitSelector.mcAspSelectionPanel.addEventListener(IntroOutroAnimEvent.FINISH,this.OnTraitSelectorPanelClose,false,0,true);
         this.mcTraitSelector.HideGhostButton();
         if(SystemUtils.UsingController && this.mcTraitSelector.ShouldFocusMoleculeOnPanelClose())
         {
            this.mcTraitSelector.FocusBackToMolecule();
         }
      }
      
      protected function OnMouseDown(param1:MouseEvent) : void
      {
         if(this.IsTraitReassignment())
         {
            return;
         }
         if(!DisplayObjectUtils.IsParent(this.mcTraitSelector,param1.target as DisplayObject))
         {
            this.CloseSubpanels();
         }
      }
      
      protected function OnTraitRandomize(param1:TraitSelectorTraitEvent) : void
      {
         this.mTraitSelectionData.RandomizeTraits();
         var _loc2_:Array = this.mTraitSelectionData.SelectedTraitIds;
         if(!this.IsTraitReassignment() && Boolean(this.mCurrentDialog.current_personality_trait_ids.length))
         {
            _loc2_ = this.mCurrentDialog.current_personality_trait_ids.concat(_loc2_);
         }
         var _loc3_:Vector.<TraitsStaticData> = new Vector.<TraitsStaticData>(_loc2_.length);
         var _loc4_:int = 0;
         var _loc5_:int = int(_loc2_.length);
         while(_loc4_ < _loc5_)
         {
            _loc3_[_loc4_] = TraitsStaticData.GetStaticData(_loc2_[_loc4_]);
            _loc4_ = _loc4_ + 1;
         }
         var _loc6_:Object = this.mcTraitSelector.GetMoleculeData();
         _loc6_["simData"]["traits"] = _loc3_;
         this.mcTraitSelector.SetMoleculeData(_loc6_);
         this.mcTraitSelector.HideGhostButton();
         this.UpdateOkButton();
      }
      
      protected function ShowNextDialog() : void
      {
         var _loc3_:TraitsStaticData = null;
         var _loc4_:* = undefined;
         var _loc5_:int = 0;
         var _loc6_:Array = null;
         var _loc7_:HouseholdSimData = null;
         var _loc8_:Array = null;
         var _loc9_:Vector.<TraitsStaticData> = null;
         var _loc10_:String = null;
         var _loc11_:int = 0;
         var _loc12_:int = 0;
         var _loc13_:int = 0;
         var _loc14_:Object = null;
         var _loc1_:SimPersonalityAssignmentDialog = this.mDialogMsgQueue.shift();
         this.mCurrentDialog = _loc1_;
         this.mDialogId = _loc1_.dialog.dialog_id;
         this.mSimId = _loc1_.sim_id;
         var _loc2_:Number = this.mcBg.width - AgeUpPanelTunables.TITLE_PADDING.Horizontal;
         TextUtils.ResizeTextToFit(this.txtTitle,_loc1_.dialog.title ? _loc1_.dialog.title.toString() : "",_loc2_,this.txtTitle.height);
         this.txtSubTitle.htmlText = _loc1_.secondary_title ? _loc1_.secondary_title.toString() : "";
         this.txtSubTitle.visible = this.txtSubTitle.length > 0;
         this.mcSimImageContainer.visible = false;
         this.mcReplaceTraitClip.visible = false;
         if(_loc1_.replace_trait_id)
         {
            _loc3_ = TraitsStaticData.GetStaticData(_loc1_.replace_trait_id);
            if(_loc3_)
            {
               _loc4_ = {"simId":this.mSimId};
               this.txtReplaceTraitName.htmlText = _loc3_.GetTitleStringBySimIdToken(_loc4_);
               this.mcReplaceTraitIcon.LoadImage(_loc3_.GetIconBySimIdToken(_loc4_));
               this.mcReplaceTraitClip.visible = true;
            }
         }
         if(_loc1_.naming_title_text)
         {
            _loc5_ = CommunicationManager.CallGameService("GetSimSpecies",this.mSimId) as uint;
            this.mcNamePanel.SetData(_loc1_.naming_title_text.toString(),_loc1_.is_female,_loc5_,_loc1_.dialog);
            this.mcNamePanel.visible = true;
            this.mcInfoPanel.visible = this.mcTraitSelector.visible = false;
            if(GameContent.HAS_EP21 && Species.IsHuman(_loc5_))
            {
               this.mcNamePanel.SetParentData(_loc1_.pregnancy_parent_id,_loc1_.parent_partner_id,_loc1_.parent_pregnancy_partner_id,_loc1_.parent_partner_relbit_id);
               if(_loc1_.pregnancy_parent_id)
               {
                  this.mcSimImageContainer.visible = true;
                  ImageUtils.LoadSimThumbnail(this.mcSimImageContainer.mcImage,_loc1_.pregnancy_parent_id,ImageUtils.SIM_THUMBNAIL_TYPE_BUST,ImageUtils.THUMBNAIL_SIZE_MEDIUM);
               }
            }
         }
         else if(_loc1_.available_aspiration_ids.length > 0 || _loc1_.available_personality_trait_ids.length > 0)
         {
            this.mcInfoPanel.SetData(_loc1_);
            if(this.IsTraitReassignment())
            {
               this.mOriginalTraitIds = _loc1_.current_personality_trait_ids.concat();
               this.GetTraitConflicts(_loc1_.current_personality_trait_ids);
               this.mTraitSelectionData.SetTraitList(int(_loc1_.available_trait_slots),_loc1_.available_personality_trait_ids,this.mSimId,_loc1_.current_personality_trait_ids.concat());
            }
            else
            {
               this.mTraitSelectionData.SetTraitList(int(_loc1_.available_trait_slots),_loc1_.available_personality_trait_ids,this.mSimId);
            }
            this.mAspirationSelectionData.SetAspirationList(_loc1_.available_aspiration_ids,this.mSimId);
            this.mcTraitSelector.SetSelectionData(this.mTraitSelectionData,this.mAspirationSelectionData,this.mSimId);
            this.mcTraitSelector.mcTraitsMolecule.SetTraitRandomizeVisible(true);
            this.mcTraitSelector.mcTraitsMolecule.SetTraitRandomizeEnabled(true);
            this.mcTraitSelector.addEventListener(TraitSelectorTraitEvent.RANDOMIZE,this.OnTraitRandomize,false,0,true);
            _loc6_ = new Array();
            _loc7_ = this.mTraitMoleculeData;
            _loc7_.age = new AgeUpdate(CommunicationManager.CallGameService("GetSimAge",this.mSimId)).age;
            _loc7_.aspiration = AspirationTrackStaticData.GetTrackData(_loc1_.current_aspiration_id);
            _loc7_.bonusTrait = _loc1_.current_aspiration_trait_id ? TraitsStaticData.GetStaticData(_loc1_.current_aspiration_trait_id) : null;
            _loc6_.push(_loc1_.current_aspiration_id);
            if(_loc7_.bonusTrait)
            {
               _loc6_.push(_loc7_.bonusTrait.id);
            }
            _loc8_ = _loc1_.current_personality_trait_ids;
            _loc9_ = new Vector.<TraitsStaticData>();
            for each(_loc10_ in _loc8_)
            {
               _loc9_.push(TraitsStaticData.GetStaticData(_loc10_));
               if(_loc1_.dialog.dialog_style != DialogTypes.STYLE_TRAIT_REASSIGNMENT)
               {
                  _loc6_.push(_loc10_);
               }
            }
            _loc11_ = int(_loc1_.available_trait_slots);
            _loc12_ = this.IsTraitReassignment() && Boolean(_loc1_.current_personality_trait_ids) ? int(_loc11_ - _loc1_.current_personality_trait_ids.length) : _loc11_;
            _loc13_ = 0;
            while(_loc13_ < _loc12_)
            {
               _loc9_.push(null);
               _loc13_ = _loc13_ + 1;
            }
            _loc7_.traits = _loc9_;
            _loc14_ = {"simId":_loc1_.sim_id};
            this.mcTraitSelector.SetMoleculeData({
               "simData":this.mTraitMoleculeData,
               "lockedData":_loc6_,
               "locToken":_loc14_
            });
            this.mcTraitSelector.HideGhostButton();
            this.mcNamePanel.visible = false;
            this.mcInfoPanel.visible = this.mcTraitSelector.visible = true;
         }
         else
         {
            this.mcInfoPanel.SetData(_loc1_);
            this.mcNamePanel.visible = this.mcTraitSelector.visible = false;
            this.mcInfoPanel.visible = true;
         }
         if(_loc1_.dialog.dialog_style == DialogTypes.STYLE_TRAIT_REASSIGNMENT)
         {
            MouseKeyboardVisibilityExtension.SetVisible(this.btnClose,true);
            this.mcBalloons.visible = false;
            this.mcSimImageContainer.visible = true;
            ImageUtils.LoadSimThumbnail(this.mcSimImageContainer.mcImage,this.mSimId,ImageUtils.SIM_THUMBNAIL_TYPE_BUST,ImageUtils.THUMBNAIL_SIZE_MEDIUM);
            this.mcTraitSelector.OverridePanelShowHide = true;
            this.mcTraitSelector.SetPanelVisible(this.mcTraitSelector.TraitPanelId,true);
         }
         else
         {
            MouseKeyboardVisibilityExtension.SetVisible(this.btnClose,false);
            this.mcBalloons.visible = true;
            this.mcTraitSelector.OverridePanelShowHide = false;
            this.mcTraitSelector.SetPanelVisible(this.mcTraitSelector.TraitPanelId,false);
         }
         if(SystemUtils.UsingController)
         {
            if(!this.mcTraitSelector.visible)
            {
               NavManager.Instance.FocusPan(this.mOkInputAdapter);
            }
         }
         this.ResizePanel();
         this.UpdateOkButton();
         this.A11yFocusPanel();
      }
      
      protected function ResizePanel() : void
      {
         var _loc2_:Number = NaN;
         var _loc1_:Point = new Point();
         DisplayObjectUtils.StretchHorizontally(this.txtTitle,this.mcBg,AgeUpPanelTunables.TITLE_PADDING);
         DisplayObjectUtils.CenterHorizontallyWithinObject([this.txtTitle],this.mcBg,0);
         _loc1_ = DisplayObjectUtils.StackVertically(this.txtTitle,AgeUpPanelTunables.TITLE_PADDING,_loc1_);
         if(this.txtSubTitle.visible)
         {
            DisplayObjectUtils.StretchHorizontally(this.txtSubTitle,this.mcBg,AgeUpPanelTunables.SUBTITLE_PADDING);
            _loc1_ = DisplayObjectUtils.StackVertically(this.txtSubTitle,AgeUpPanelTunables.SUBTITLE_PADDING,_loc1_);
         }
         if(this.mcReplaceTraitClip.visible)
         {
            DisplayObjectUtils.CenterHorizontallyWithinObject([this.mcReplaceTraitClip],this.mcBg,0);
            _loc1_ = DisplayObjectUtils.StackVertically(this.mcReplaceTraitClip,AgeUpPanelTunables.REPLACE_TRAIT_PADDING,_loc1_);
         }
         if(this.mcNamePanel.visible)
         {
            DisplayObjectUtils.StretchHorizontally(this.mcNamePanel,this.mcBg,AgeUpPanelTunables.NAME_PANEL_PADDING);
            _loc1_ = DisplayObjectUtils.StackVertically(this.mcNamePanel,AgeUpPanelTunables.NAME_PANEL_PADDING,_loc1_);
         }
         else if(this.mcTraitSelector.visible)
         {
            DisplayObjectUtils.StackVertically(this.mcInfoPanel,AgeUpPanelTunables.INFO_PANEL_PADDING_WITH_MOLECULE,_loc1_);
            this.mcTraitSelector.x = AgeUpPanelTunables.TRAIT_SELECTOR_PADDING.mLeft;
            this.mcTraitSelector.y = _loc1_.y + AgeUpPanelTunables.TRAIT_SELECTOR_PADDING.mTop;
            _loc2_ = this.IsTraitReassignment() ? this.mcTraitSelector.height : this.mcTraitSelector.GetTotalHeight();
            _loc1_.y = _loc1_.y + (_loc2_ + AgeUpPanelTunables.TRAIT_SELECTOR_PADDING.mBot);
         }
         else if(this.mcInfoPanel.visible)
         {
            _loc1_ = DisplayObjectUtils.StackVertically(this.mcInfoPanel,AgeUpPanelTunables.INFO_PANEL_PADDING_WITHOUT_MOLECULE,_loc1_);
         }
         DisplayObjectUtils.AnchorRight(this.btnOk,this.mcBg,AgeUpPanelTunables.OK_BUTTON_PADDING);
         _loc1_ = DisplayObjectUtils.StackVertically(this.btnOk,AgeUpPanelTunables.OK_BUTTON_PADDING,_loc1_);
         this.mcBg.height = _loc1_.y;
         this.HandleStageResized(LayoutAPI.StageWidth,LayoutAPI.StageHeight);
      }
      
      protected function OnTraitsChanged(param1:Event = null) : void
      {
         if(this.IsTraitReassignment())
         {
            this.GetTraitConflicts(this.mTraitSelectionData.SelectedTraitIds);
         }
         this.mcTraitSelector.HideGhostButton();
         this.UpdateOkButton();
      }
      
      protected function UpdateOkButton() : void
      {
         var _loc2_:Boolean = false;
         var _loc3_:int = 0;
         var _loc4_:int = 0;
         var _loc1_:Boolean = false;
         if(this.mcNamePanel.visible)
         {
            _loc1_ = this.mcNamePanel.IsCompleted;
         }
         else if(this.mcTraitSelector.visible)
         {
            _loc2_ = false;
            _loc3_ = 0;
            _loc4_ = int(this.mTraitMoleculeData.traits.length);
            while(_loc3_ < _loc4_)
            {
               if(this.mTraitMoleculeData.traits[_loc3_] != null)
               {
                  _loc2_ = true;
                  break;
               }
               _loc3_ = _loc3_ + 1;
            }
            if(this.IsTraitReassignment())
            {
               _loc1_ = _loc2_;
            }
            else
            {
               _loc1_ = (this.mAspirationSelectionData.length == 0 || this.mTraitMoleculeData.aspiration != null) && _loc2_;
            }
         }
         else
         {
            _loc1_ = true;
         }
         this.btnOk.enabled = _loc1_;
         if(_loc1_)
         {
            this.btnOk.TooltipExt.SetText(Keys.GENERIC_DONE);
         }
         else if(this.IsTraitReassignment())
         {
            this.btnOk.TooltipExt.SetText(KeysGP.AGE_UP_PANEL_BUTTON_DISABLE_TOOLTIP_NO_TRAITS);
         }
         else
         {
            this.btnOk.TooltipExt.SetText(this.mcNamePanel.visible ? KeysGP.AGE_UP_PANEL_BUTTON_DISABLE_TOOLTIP_NO_NAME : KeysGP.AGE_UP_PANEL_BUTTON_DISABLE_TOOLTIP);
         }
      }
      
      protected function GetTraitConflicts(param1:Array) : void
      {
         var _loc2_:Array = this.mTraitSelectionData.SelectedTraitIds;
         var _loc3_:Object = CommunicationManager.CallGameService("GetTraitConflictsForIds",{"trait_ids":param1},true);
         if(_loc3_)
         {
            TraitsStaticData.ClearStaticDataTraitConflicts();
            TraitsStaticData.SetStaticDataTraitConflicts(_loc3_);
         }
         if(this.mcTraitSelector.visible)
         {
            this.mTraitSelectionData.MarkRangeDirty(0,this.mTraitSelectionData.length - 1);
         }
      }
      
      protected function FinalizePersonalityAssignments() : void
      {
         var _loc1_:int = 0;
         var _loc2_:int = 0;
         var _loc3_:TraitsStaticData = null;
         var _loc4_:int = 0;
         var _loc5_:int = 0;
         var _loc6_:int = 0;
         if(this.IsTraitReassignment())
         {
            CommunicationManager.CallGameService("PostServerCommand",{
               "command":"traits.clear_personality_traits",
               "commandArgs":[this.mSimId]
            });
            _loc1_ = 0;
            _loc2_ = this.mTraitSelectionData.MaxTraitSelection;
            while(_loc1_ < _loc2_)
            {
               _loc3_ = this.mTraitMoleculeData.traits[_loc1_];
               if(_loc3_)
               {
                  CommunicationManager.CallGameService("PostServerCommand",{
                     "command":"traits.equip_trait",
                     "commandArgs":[_loc3_.id,this.mSimId,_loc1_]
                  });
               }
               _loc1_ = _loc1_ + 1;
            }
         }
         else
         {
            if(this.mAspirationSelectionData.length > 0)
            {
               CommunicationManager.CallGameService("PostServerCommand",{
                  "command":"ui.aspirations.set_primary",
                  "commandArgs":[this.mTraitMoleculeData.aspiration.uid,this.mSimId]
               });
               if(this.mTraitMoleculeData.bonusTrait)
               {
                  CommunicationManager.CallGameService("PostServerCommand",{
                     "command":"traits.equip_trait",
                     "commandArgs":[this.mTraitMoleculeData.bonusTrait.id,this.mSimId]
                  });
               }
            }
            if(this.mTraitSelectionData.MaxTraitSelection > 0)
            {
               _loc4_ = this.mTraitMoleculeData.traits.length - 1;
               _loc5_ = 0;
               _loc6_ = this.mTraitSelectionData.MaxTraitSelection;
               while(_loc5_ < _loc6_)
               {
                  _loc3_ = this.mTraitMoleculeData.traits[_loc4_ - _loc5_];
                  if(_loc3_)
                  {
                     CommunicationManager.CallGameService("PostServerCommand",{
                        "command":"traits.equip_trait",
                        "commandArgs":[_loc3_.id,this.mSimId]
                     });
                  }
                  _loc5_ = _loc5_ + 1;
               }
            }
         }
      }
      
      protected function IsTraitReassignment() : Boolean
      {
         return Boolean(this.mCurrentDialog) && this.mCurrentDialog.dialog.dialog_style == DialogTypes.STYLE_TRAIT_REASSIGNMENT;
      }
      
      protected function InitializeGamepadInput() : void
      {
         var _loc1_:Vector.<DisplayObject> = new <DisplayObject>[this.btnOk];
         this.mOkInputAdapter = new BidirectionalGroupAdapter(_loc1_);
         this.mOkInputAdapter.OnLeaveCall(this.HandleOkAdapterLeave);
         this.mOkInputAdapter.OnBackCall(this.HandleBack);
         var _loc2_:Vector.<DisplayObject> = new <DisplayObject>[this.mcNamePanel.txtFirstName,this.mcNamePanel.btnFirstNameDice,this.mcNamePanel.txtLastName,this.mcNamePanel.btnLastNameDice,this.mcNamePanel.ddSecretChild,this.mcNamePanel.ddSelectDynasty];
         this.mAdoptionInputAdapter = new OmnidirectionalGroupAdapter();
         this.mAdoptionInputAdapter.SetElements(_loc2_);
         this.mAdoptionInputAdapter.OnConfirmCall(this.HandleAdoptionConfirm);
         this.mAdoptionInputAdapter.OnLeaveCall(this.HandleContentAdapterLeave);
         var _loc3_:TextInput = this.mcNamePanel.txtFirstName;
         _loc3_.SetupVirtualKeyboardParams(this.OnVKeyboardOutput);
         _loc3_ = this.mcNamePanel.txtLastName;
         _loc3_.SetupVirtualKeyboardParams(this.OnVKeyboardOutput);
         this.mcTraitSelector.OnInputEventCall(InputAdapterEvent.LEAVE,this.HandleContentAdapterLeave);
         this.mcTraitSelector.OnInputEventCall(InputAdapterEvent.BACK,this.HandleBack);
         this.mcTraitSelector.addEventListener(TraitSelector.CLOSE_PANELS_EVENT,this.CloseSubpanels,false,0,true);
         this.mcTraitSelector.mcTraitsMolecule.mcTraitGridView.addEventListener(GridEvent.CELL_EVENT.concat(PushButtonEvent.CLICK),this.HandleTraitMoleculeConfirm);
         this.mScrollAction = InputAction.WhenTriggered(InputTrigger.FromActionCode(ActionCodes.RIGHT_STICK_MOVE_FAKE)).AllowWhileModalOpen(true).SetLegendKey(KeysConsole.GENERIC_SCROLL_TEXT);
      }
      
      protected function HandleBack() : void
      {
         if(this.IsTraitReassignment())
         {
            this.OnDialogFinished(true);
         }
      }
      
      protected function HandleTraitMoleculeConfirm(param1:GridEvent) : void
      {
         NavManager.Instance.FocusForward(this.mcTraitSelector.mcTraitSelectionPanel);
      }
      
      override public function Enter(param1:EnterParams = null) : IInputFocusable
      {
         if(this.mcTraitSelector.visible)
         {
            return this.mcTraitSelector.Enter(param1);
         }
         return this.mAdoptionInputAdapter.Enter(param1);
      }
      
      override public function Exit() : void
      {
         super.Exit();
      }
      
      protected function Tick(param1:TickerEvent) : void
      {
         var _loc2_:Number = GamepadAnalogSticks.ApplyDeadzoneToValue(GamepadAnalogSticks.GetRightY());
         if(_loc2_ != 0)
         {
            this.mcInfoPanel.mcTraitList.mSlider.SetCurrentValue(this.mcInfoPanel.mcTraitList.mSlider.Value - _loc2_ * AgeUpPanelTunables.CONSOLE_TRAITS_SLIDER_SPEED,false);
         }
      }
      
      protected function HandleAdoptionConfirm(param1:InputAdapterConfirmEvent) : void
      {
         var _loc2_:TextInput = param1.GetObj() as TextInput;
         if(_loc2_)
         {
            _loc2_.focused = 1;
         }
      }
      
      protected function OnVKeyboardOutput(param1:TextInput, param2:uint, param3:String) : void
      {
         if(param1)
         {
            if(param2 == VirtualKeyboardHelper.STATUS_COMPLETE)
            {
               param1.text = param3;
               this.mcNamePanel.SetNameInput();
            }
            param1.focused = 0;
            param1.stage.focus = null;
         }
      }
      
      protected function HandleOkAdapterLeave(param1:InputAdapterLeaveEvent) : void
      {
         if(param1.GetDirection() == NavDirection.UP)
         {
            if(this.mcTraitSelector.visible)
            {
               NavManager.Instance.FocusPan(this.mcTraitSelector,param1.CreateEnterParams());
            }
            else if(this.mcNamePanel.visible)
            {
               NavManager.Instance.FocusPan(this.mAdoptionInputAdapter,param1.CreateEnterParams());
            }
         }
      }
      
      protected function HandleContentAdapterLeave(param1:InputAdapterLeaveEvent) : void
      {
         if(param1.GetDirection() == NavDirection.DOWN)
         {
            NavManager.Instance.FocusPan(this.mOkInputAdapter,param1.CreateEnterParams());
         }
      }
      
      protected function HandleUsingControllerToggled() : void
      {
         if(this.mcTraitSelector.visible)
         {
            this.CloseSubpanels();
            this.mcTraitSelector.mcAspSelectionPanel.EnableAspirations();
         }
      }
   }
}

