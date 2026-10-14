package widgets.Dialog
{
   import flash.display.DisplayObject;
   import flash.events.TimerEvent;
   import flash.geom.Point;
   import flash.utils.Timer;
   import flash.utils.getDefinitionByName;
   import gamedata.Dialog.UiDialogCloseRequest;
   import gamedata.Dialog.UiDialogMessage;
   import gamedata.Dialog.UiDialogTextInputMessage;
   import gamedata.Exchange.ExchangeData;
   import olympus.constants.ActionCodes;
   import olympus.constants.DialogModality;
   import olympus.constants.DialogTypes;
   import olympus.constants.GameStates;
   import olympus.constants.WindowAnimation;
   import olympus.controls.EditTextField;
   import olympus.core.UISettings;
   import olympus.core.widget.WidgetBase;
   import olympus.dialog.DialogInputType;
   import olympus.dialog.DialogManager;
   import olympus.dialog.DialogRequest;
   import olympus.dialog.IDialog;
   import olympus.dialog.IDialogAction;
   import olympus.dialog.IDialogData;
   import olympus.dialog.IDialogInput;
   import olympus.gamepad.EnterParams;
   import olympus.gamepad.NavManager;
   import olympus.input.IInputAdapter;
   import olympus.input.IInputFocusable;
   import olympus.input.InputAction;
   import olympus.input.InputTrigger;
   import olympus.input.adapters.DynamicOmniPointAdapter;
   import olympus.input.adapters.DynamicOmnidirectionalAdapter;
   import olympus.input.adapters.InputAdapterConfirmEvent;
   import olympus.input.adapters.InputAdapterEvent;
   import olympus.input.helpers.LinkInputProxy;
   import olympus.input.helpers.VirtualKeyboardHelper;
   import olympus.core.TooltipManager;
   import olympus.io.CommunicationManager;
   import olympus.io.TelemetryManager;
   import olympus.localization.Keys;
   import olympus.localization.LocKey;
   import olympus.objects.IconInfo;
   import olympus.utils.DisplayObjectUtils;
   import olympus.utils.Random;
   import olympus.utils.SystemUtils;
   import olympus.utils.WidgetUtils;
   import scaleform.clik.controls.TextInput;
   import widgets.Dialog.actions.CallbackDialogAction;
   import widgets.Dialog.actions.MessageDialogAction;
   import widgets.Dialog.actions.NullDialogAction;
   import widgets.Dialog.constants.DialogTunables;
   import widgets.Dialog.constants.GenericDialogOption;
   import widgets.Dialog.data.InfoSettingDialogData;
   import widgets.Dialog.data.LocalCheckBoxRequestData;
   import widgets.Dialog.data.LocalRequestData;
   import widgets.Dialog.data.MovieClipDialogData;
   import widgets.Dialog.data.ServerRequestData;
   import widgets.Dialog.dialogs.ConnectionDialog;
   import widgets.Dialog.dialogs.DialogContainer;
   import widgets.Dialog.dialogs.ExchangeLegalNoticeDialog;
   import widgets.Dialog.dialogs.ModScriptsDialog;
   import widgets.Dialog.dialogs.MovieClipDialog;
   import widgets.Dialog.dialogs.SavingDialog;
   import widgets.Dialog.dialogs.SimInteractionDialog;
   import widgets.Dialog.dialogs.TutorialDialog;
   import widgets.Dialog.footers.CheckBoxConfirmFooter;
   import widgets.Dialog.footers.DialogButtonFooter;
   import widgets.Dialog.footers.DialogFooterCellView;
   import widgets.Dialog.footers.ReplayFooter;
   import widgets.Dialog.footers.YesButtonsFooter;
   import widgets.Dialog.footers.YesNoFooter;
   import widgets.Dialog.headers.CheckboxSettingHeader;
   import widgets.Dialog.headers.DialogDynamicSign;
   import widgets.Dialog.headers.DialogHeaderCellView;
   import widgets.Dialog.headers.GridIconButtonsHeader;
   import widgets.Dialog.headers.IconsLabelsHeader;
   import widgets.Dialog.headers.InfoColumnsHeader;
   import widgets.Dialog.headers.PaymentInputHeader;
   import widgets.Dialog.headers.PhotoMontageHeader;
   import widgets.Dialog.headers.TextInputIconSelectHeader;
   import widgets.Dialog.headers.TextInputImageHeader;
   import widgets.Dialog.headers.TitleBodyHeader;
   import widgets.Dialog.headers.TitleBodyImageHeader;
   import widgets.Dialog.headers.VariableInputHeader;
   import widgets.Dialog.inputs.TextDialogInput;
   import widgets.Gameplay.SimInfoHUD.AspirationPanel.AspirationTooltip;
   import widgets.shared.constants.DownloadSharedTunables;
   import widgets.shared.controls.Console.LegendItemWrapper;
   import widgets.shared.utils.SharedTutorialUtils;
   
   public class DialogMain extends WidgetBase
   {
      
      protected static const NUMBER_TO_STRING_NAME:Array = new Array("Zero","One","Two","Three","Four","Five","Six");
      
      protected var mDialogManager:DialogManager;
      
      protected var mDownloadCompleteDelayTimer:Timer;
      
      protected var mDynamicOmniInputAdapter:DynamicOmniPointAdapter;
      
      protected var mCurrentDialogInputFocusStack:Array = [];
      
      protected var bUseThisForFocusBack:Boolean;
      
      public function DialogMain()
      {
         super();
      }
      
      protected static function LegacyCreateDialogAction(param1:String, param2:Object, param3:Boolean = false) : IDialogAction
      {
         var _loc5_:String = null;
         var _loc12_:Array = null;
         var _loc4_:Object = param2[param1 + "Callback"];
         if(param3)
         {
            _loc12_ = ["?","?"];
            _loc5_ = _loc12_.join("-");
         }
         else
         {
            _loc5_ = ConvertIfLocKey(param2[param1 + "Text"]);
         }
         var _loc6_:Object = param2[param1 + "Params"];
         var _loc7_:Boolean = param2[param1 + "Enabled"] != undefined ? Boolean(param2[param1 + "Enabled"]) : true;
         var _loc8_:String = ConvertIfLocKey(param2[param1 + "TooltipText"]);
         var _loc9_:String = param2[param1 + "Audio"] != undefined ? param2[param1 + "Audio"] : null;
         var _loc10_:String = param2[param1 + "SubLabel"] != undefined ? param2[param1 + "SubLabel"] : null;
         if(_loc5_ == null)
         {
            return null;
         }
         var _loc11_:String = _loc4_ as String;
         if(_loc11_)
         {
            return new MessageDialogAction(_loc11_,_loc6_,_loc5_,_loc7_,_loc8_,_loc9_,null,_loc10_);
         }
         if(_loc4_ != null)
         {
            return new CallbackDialogAction(_loc4_,_loc6_,_loc5_,_loc7_,_loc8_,_loc9_,null,_loc10_);
         }
         return new NullDialogAction(_loc5_,_loc7_,_loc8_,_loc9_,null,_loc10_);
      }
      
      protected static function ConvertIfLocKey(param1:Object) : String
      {
         if(param1 == null)
         {
            return null;
         }
         if(param1 is String)
         {
            return param1 as String;
         }
         var _loc2_:LocKey = param1 is LocKey ? param1 as LocKey : new LocKey(param1);
         if(_loc2_.IsValid())
         {
            return _loc2_.toString();
         }
         return param1.toString();
      }
      
      public static function ElementShouldBeAdded(param1:DisplayObject) : Boolean
      {
         return !DisplayObjectUtils.GetParentClassByString(param1,"widgets.Gameplay.BusinessEmployeeManagement.controls::EmployeeCellView") && !DisplayObjectUtils.GetParentClassByString(param1,"widgets.Dialog.controls::IconLabelCellView") && !(param1 is LegendItemWrapper) && (param1 is TextInput || param1 is LinkInputProxy || DynamicOmnidirectionalAdapter.DefaultElementShouldBeAdded(param1));
      }
      
      override public function Initialize() : void
      {
         CommunicationManager.RegisterServiceHandler("IsConnectionDialogShown",this.HandleIsConnectionDialogShown,this);
         CommunicationManager.RegisterServiceHandler("HideConnectionDialog",this.HandleHideConnectionDialog,this);
         AddMessageListener("ShowConnectionDialog",this.HandleShowConnectionDialog);
         AddMessageListener("UiDialogCloseRequest",this.HandleUiDialogCloseRequest,UiDialogCloseRequest);
         AddMessageListener("ShowSavingDialog",this.HandleShowSavingDialog);
         AddMessageListener("ShowExchangeLegalNoticeDialog",this.HandleShowExchangeLegalNoticeDialog);
         AddMessageListener("ShowTutorialDialog",this.HandleShowTutorialDialog);
         AddMessageListener("GameStateLoadComplete",this.HandleGameStateLoadComplete);
         AddMessageListener("ShowFTUEDialog",this.HandleShowFTUEDialog);
         AddMessageListener("ShowCDSContentInstalledDialog",this.ShowCDSContentInstalledDialog);
         AddMessageListener("ShowCDSContentInstalledDialogWithTelemetry",this.ShowCDSContentInstalledDialogWithTelemetry);
         AddMessageListener("DownloadStateChanged",this.TriggerDownloadCompleteDialog);
         SharedTutorialUtils.AddListeners();
         this.mDialogManager = new DialogManager(this);
         if(SystemUtils.UsingConsoleInputMode)
         {
            this.InitGamepad();
         }
      }
      
      override public function Unload() : void
      {
         SharedTutorialUtils.RemoveListeners();
      }
      
      override public function Show(param1:Object = null) : void
      {
         var _loc4_:IDialogAction = null;
         var _loc9_:int = 0;
         var _loc12_:String = null;
         var _loc13_:UiDialogTextInputMessage = null;
         var _loc14_:TextDialogInput = null;
         var _loc15_:Array = null;
         var _loc16_:IDialogInput = null;
         super.Show(param1);
         if(SystemUtils.UsingConsoleInputMode)
         {
            if(this.mDynamicOmniInputAdapter)
            {
               this.mDynamicOmniInputAdapter.SetupDefaultVirtualKeyboardParams(this.OnVKeyboardOutput);
               this.mDynamicOmniInputAdapter.UpdateElements();
            }
         }
         if(!param1)
         {
            return;
         }
         if(param1 is UiDialogMessage)
         {
            this.HandleUiDialogMessage(param1 as UiDialogMessage);
            return;
         }
         var _loc2_:LocalRequestData = new LocalRequestData();
         if("dialog_id" in param1)
         {
            _loc2_.dialog_id = param1["dialog_id"];
         }
         var _loc3_:Boolean = Boolean(CommunicationManager.CallGameService("GetDialogButtonsSettings"));
         var _loc5_:int = int(param1["type"]);
         var _loc6_:int = DialogTypes.GetNumButtons(_loc5_);
         var _loc7_:int = DialogTypes.GetNumInputFields(_loc5_);
         _loc2_.dialogType = _loc5_;
         if(param1["optionOneText"] == null)
         {
            param1["optionOneText"] = _loc5_ == DialogTypes.SINGLE_BUTTON ? Keys.GENERIC_OK.toString() : Keys.GENERIC_YES.toString();
         }
         if(_loc6_ >= 2 && param1["optionTwoText"] == null)
         {
            param1["optionTwoText"] = Keys.GENERIC_NO.toString();
         }
         var _loc8_:Number = Random.Num(-50,50);
         _loc9_ = 1;
         while(_loc9_ <= _loc6_ && _loc9_ < NUMBER_TO_STRING_NAME.length)
         {
            if(_loc3_ == false || _loc8_ < 0)
            {
               _loc4_ = LegacyCreateDialogAction("option" + NUMBER_TO_STRING_NAME[_loc9_],param1);
            }
            else
            {
               _loc4_ = LegacyCreateDialogAction("option" + NUMBER_TO_STRING_NAME[_loc6_ + 1 - _loc9_],param1,_loc3_);
            }
            if(_loc4_)
            {
               _loc2_.actions.push(_loc4_);
            }
            _loc9_++;
         }
         if(Boolean(param1["closeCallback"]) || Boolean(param1["closeText"]))
         {
            param1["closeText"] = param1["closeText"] || "";
            _loc4_ = LegacyCreateDialogAction("close",param1);
            if(_loc4_)
            {
               _loc2_.cancellationAction = _loc4_;
            }
         }
         if(_loc7_ == 1 || Boolean(param1["numInputs"]))
         {
            if(param1["numInputs"] != null)
            {
               _loc7_ = int(param1["numInputs"]);
            }
            if(_loc7_ == 1)
            {
               if(param1["textInputOneName"] == null)
               {
                  param1["textInputOneName"] = "textInput";
               }
            }
            _loc9_ = 0;
            while(_loc9_ < _loc7_)
            {
               _loc12_ = param1["textInputOneName"] ? param1["textInputOneName"] : "textInputField" + _loc9_.toString();
               _loc13_ = new UiDialogTextInputMessage({
                  "text_input_name":_loc12_,
                  "min_length":int(param1["minTextChar"]),
                  "max_length":int(param1["maxTextChar"])
               });
               if(param1["inputFieldTitles"])
               {
                  _loc15_ = param1["inputFieldTitles"];
                  _loc13_.title = _loc15_[_loc9_] as LocKey;
               }
               _loc14_ = new TextDialogInput(_loc13_);
               _loc14_.defaultTextOverride = ConvertIfLocKey(param1["defaultText"]);
               _loc14_.value = ConvertIfLocKey(param1["initialText"]);
               _loc2_.inputs.push(_loc14_);
               _loc9_++;
            }
         }
         if(!("description" in param1))
         {
            param1["description"] = param1["title"];
            param1["title"] = null;
         }
         if("iconSimId" in param1)
         {
            _loc2_.iconSimId = param1["iconSimId"];
         }
         _loc2_.promptText = ConvertIfLocKey(param1["description"]);
         _loc2_.title = ConvertIfLocKey(param1["title"]);
         _loc2_.options = uint(param1["options"]);
         _loc2_.icon = param1["icon"];
         _loc2_.dialogStyle = param1["dialogStyle"];
         _loc2_.dialogBackgroundStyle = param1["dialogBackgroundStyle"];
         if("optionDropdowns" in param1)
         {
            for each(_loc16_ in param1["optionDropdowns"])
            {
               _loc2_.inputs.push(_loc16_);
            }
         }
         var _loc10_:IDialog = this.GetDialogFromData(_loc2_);
         var _loc11_:DialogRequest = new DialogRequest(_loc10_,_loc2_);
         _loc11_.modality = "modality" in param1 ? int(param1["modality"]) : DialogModality.GAMEPLAY;
         param1.final_dialog_id = DialogManager.RequestDialog(_loc11_);
      }
      
      override public function Hide(param1:Object = null) : void
      {
         var _loc2_:IInputFocusable = null;
         super.Hide(param1);
         if(SystemUtils.UsingController)
         {
            _loc2_ = this.bUseThisForFocusBack ? this : this.mCurrentDialogInputFocusStack[0];
            NavManager.Instance.TryFocusBack(_loc2_);
         }
         if(SystemUtils.UsingConsoleInputMode)
         {
            CommunicationManager.SendUIMessage("ShowCurrentNarrationSubtitle");
         }
      }
      
      override public function HandleStageResized(param1:Number, param2:Number) : void
      {
         super.HandleStageResized(param1,param2);
         if(this.mDialogManager)
         {
            this.mDialogManager.StageResized(param1,param2);
         }
      }
      
      protected function HandleGameStateLoadComplete(param1:uint) : void
      {
         if(param1 != GameStates.MAIN_MENU)
         {
            return;
         }
         RemoveMessageListener("GameStateLoadComplete",this.HandleGameStateLoadComplete);
         var _loc2_:Object = UISettings.AccountSettings.GetValue("options.hide64BitWarning",ExchangeData.LocalOriginId);
         if(_loc2_ == null || !_loc2_)
         {
            CommunicationManager.CallGameService("OptionsCheckSupported64Bit");
         }
         var _loc3_:Object = UISettings.AccountSettings.GetValue("options.hideInsufficientMemoryForPackWarning",ExchangeData.LocalOriginId);
         if(!_loc3_)
         {
            CommunicationManager.CallGameService("OnOptionsCheckSufficientMemoryForPacks");
         }
         CommunicationManager.CallGameService("OptionsCheckSupportedVideoCard");
         if(CommunicationManager.CallGameService("OptionsIsModsDisabledDueToPatch"))
         {
            CommunicationManager.SendUIMessage("ShowDialog",{
               "type":DialogTypes.SINGLE_BUTTON,
               "title":Keys.OPTIONS_MODS_DISABLED_TITLE.toString(),
               "description":Keys.OPTIONS_MODS_DISABLED_DESC.toString(),
               "optionOneText":Keys.GENERIC_OK.toString()
            });
         }
         if(CommunicationManager.CallGameService("OptionsGetShowModsAtStartup"))
         {
            ModScriptsDialog.Show();
         }
      }
      
      public function A11yFocusDialog(param1:Object) : void
      {
         var _loc2_:DisplayObject = null;
         try
         {
            _loc2_ = param1 as DisplayObject;
            if(_loc2_ != null)
            {
               TooltipManager.getInstance().A11yFocusInto(_loc2_);
            }
         }
         catch(e:Error)
         {
         }
      }

      public function A11yAnnounceDialog(param1:Object) : void
      {
         var _loc2_:String = null;
         var _loc3_:String = null;
         var _loc4_:Object = null;
         try
         {
            _loc4_ = param1;
            _loc2_ = "";
            if(_loc4_["title"] != null)
            {
               _loc2_ = _loc4_["title"].toString();
            }
            if(_loc4_["text"] != null)
            {
               if(_loc2_.length > 0)
               {
                  _loc2_ += ". ";
               }
               _loc2_ += _loc4_["text"].toString();
            }
            if(_loc2_.length == 0)
            {
               return;
            }
            _loc3_ = encodeURIComponent(_loc2_);
            _loc3_ = _loc3_.split("'").join("%27");
            _loc3_ = _loc3_.split("(").join("%28");
            _loc3_ = _loc3_.split(")").join("%29");
            _loc3_ = _loc3_.split("!").join("%21");
            var manager:Object = getDefinitionByName("olympus.core.TooltipManager")["getInstance"]();
            if(manager != null && "A11yPostToPython" in manager) { manager["A11yPostToPython"]("a11y.dialog_enc",_loc3_); }
            else { CommunicationManager.PostServerCommand("a11y.dialog_enc",_loc3_); }
         }
         catch(e:Error)
         {
         }
      }

      protected function HandleUiDialogMessage(param1:UiDialogMessage) : void
      {
         var _loc2_:IDialog = null;
         var _loc3_:IDialogData = null;
         var _loc4_:DialogRequest = null;
         var _loc5_:MovieClipDialogData = null;
         var _loc6_:DialogContainer = null;
         var _loc7_:DialogContainer = null;
         var _loc8_:DialogContainer = null;
         var _loc9_:* = undefined;
         switch(param1.dialog_type)
         {
            case UiDialogMessage.TYPE_OBJECT_MULTI_PICKER:
            case UiDialogMessage.TYPE_OBJECT_PICKER:
            case UiDialogMessage.TYPE_CUSTOMIZE_OBJECT_MULTI_PICKER:
               return;
            case UiDialogMessage.TYPE_NOTIFICATION:
               return;
            case UiDialogMessage.TYPE_MOVIE_CLIP_DIALOG:
               _loc2_ = new MovieClipDialog();
               _loc5_ = new MovieClipDialogData();
               _loc5_.dialog_id = param1.dialog_id;
               _loc5_.movieclip = param1.movieclip;
               _loc3_ = _loc5_;
               _loc4_ = new DialogRequest(_loc2_,_loc3_);
               _loc4_.tweenInParams = WindowAnimation.PANEL_BOUNCE_IN;
               break;
            case UiDialogMessage.TYPE_INFO_SETTING:
               _loc3_ = new InfoSettingDialogData(param1);
               _loc6_ = new DialogContainer();
               _loc6_.Header = new CheckboxSettingHeader();
               _loc6_.Footer = new DialogButtonFooter();
               _loc2_ = _loc6_;
               break;
            case UiDialogMessage.TYPE_ICONS_LABELS:
               _loc3_ = new ServerRequestData(param1);
               _loc7_ = new DialogContainer();
               if(param1.dialog_style == DialogTypes.STYLE_LARGE_ICON || param1.dialog_style == DialogTypes.STYLE_LARGE_ICON_TEXT_HORIZONTAL || param1.dialog_style == DialogTypes.STYLE_LARGE_ICON_WIDE)
               {
                  _loc7_.Header = new TitleBodyImageHeader();
               }
               else if(param1.dialog_style == DialogTypes.STYLE_DYNAMIC_SIGN)
               {
                  _loc7_.Header = new DialogDynamicSign();
               }
               else
               {
                  _loc7_.Header = new IconsLabelsHeader();
               }
               if(_loc3_.footerType == DialogTypes.FOOTER_TYPE_YES_NO_FOOTER || _loc3_.dialogType == DialogTypes.YES || _loc3_.dialogType == DialogTypes.YES_NO)
               {
                  _loc7_.Footer = new YesNoFooter();
               }
               else if(_loc3_.footerType == DialogTypes.FOOTER_TYPE_YES_BUTTONS_FOOTER)
               {
                  _loc7_.Footer = new YesButtonsFooter();
               }
               else
               {
                  _loc7_.Footer = new DialogButtonFooter();
               }
               _loc2_ = _loc7_;
               break;
            case UiDialogMessage.TYPE_INFO_IN_COLUMNS:
               _loc3_ = new ServerRequestData(param1);
               _loc8_ = new DialogContainer();
               _loc8_.Header = new InfoColumnsHeader();
               _loc8_.Footer = this.GetFooterFromData(_loc3_);
               _loc2_ = _loc8_;
               break;
            case UiDialogMessage.TYPE_REVEAL_SEQUENCE:
               _loc3_ = new ServerRequestData(param1);
               _loc9_ = new DialogContainer();
               _loc9_.Header = new PhotoMontageHeader();
               _loc9_.Footer = new ReplayFooter();
               _loc2_ = _loc9_;
               break;
            default:
               if(param1.target_id != null && param1.target_id.length != 0 && param1.target_id != "0")
               {
                  _loc2_ = new SimInteractionDialog();
               }
               else
               {
                  _loc3_ = new ServerRequestData(param1);
                  _loc2_ = this.GetDialogFromData(_loc3_);
               }
         }
         if(_loc3_ == null)
         {
            _loc3_ = new ServerRequestData(param1);
         }
         if(_loc4_ == null)
         {
            _loc4_ = new DialogRequest(_loc2_,_loc3_);
         }
         _loc4_.modality = DialogModality.GAMEPLAY;
         DialogManager.RequestDialog(_loc4_);
         this.A11yAnnounceDialog(param1);
         // Focus follows DialogManager.GetCurrentRequest in TooltipManager.
      }
      
      protected function HandleUiDialogCloseRequest(param1:UiDialogCloseRequest) : void
      {
         DialogManager.CancelRequest(param1.dialog_id,false);
      }
      
      protected function HandleShowConnectionDialog(param1:Object) : void
      {
         ConnectionDialog.Show(param1);
      }
      
      protected function HandleIsConnectionDialogShown(param1:Object) : Boolean
      {
         return ConnectionDialog.IsShown();
      }
      
      protected function HandleHideConnectionDialog(param1:Object) : Object
      {
         var _loc2_:Boolean = Boolean(param1) && param1.hasOwnProperty("bIsStayOffline") ? Boolean(param1["bIsStayOffline"]) : Boolean(null);
         var _loc3_:Boolean = Boolean(param1) && param1.hasOwnProperty("bNetworkConnectionHandler") ? Boolean(param1["bNetworkConnectionHandler"]) : Boolean(null);
         return ConnectionDialog.Hide(_loc2_,_loc3_);
      }
      
      protected function HandleShowSavingDialog(param1:Object) : void
      {
         var _loc2_:LocalRequestData = null;
         var _loc3_:IDialog = null;
         if(CommunicationManager.CallUIService("IsUILoading"))
         {
            return;
         }
         _loc2_ = new LocalRequestData();
         _loc3_ = new SavingDialog();
         _loc2_.title = param1["title"];
         _loc2_.dialog_id = param1["dialog_id"];
         _loc2_.options = param1["options"];
         var _loc4_:DialogRequest = new DialogRequest(_loc3_,_loc2_);
         _loc4_.modality = DialogModality.SYSTEM;
         DialogManager.RequestDialog(_loc4_);
      }
      
      protected function HandleShowExchangeLegalNoticeDialog(param1:Object) : void
      {
         var _loc2_:LocalRequestData = null;
         var _loc3_:IDialog = null;
         _loc2_ = new LocalRequestData();
         _loc2_.dialog_id = "LegalNoticeDialogId";
         _loc3_ = new ExchangeLegalNoticeDialog(param1.callback,param1.callbackArgs);
         _loc2_.cancellationAction = new CallbackDialogAction(ExchangeLegalNoticeDialog.OnCancel,_loc3_,null);
         var _loc4_:DialogRequest = new DialogRequest(_loc3_,_loc2_);
         _loc4_.modality = DialogModality.GAMEPLAY;
         DialogManager.RequestDialog(_loc4_);
      }
      
      protected function HandleShowTutorialDialog(param1:Object) : void
      {
         var _loc2_:LocalRequestData = null;
         var _loc3_:IDialog = null;
         _loc2_ = new LocalRequestData();
         _loc2_.dialog_id = param1.dialogId;
         _loc2_.options = param1["options"];
         _loc2_.actions.push(LegacyCreateDialogAction("optionOne",param1));
         _loc2_.actions.push(LegacyCreateDialogAction("optionTwo",param1));
         _loc2_.cancellationAction = _loc2_.actions[1];
         _loc2_.title = param1["title"];
         _loc2_.icon = param1["icon"];
         _loc2_.promptText = Keys.TUTORIAL_TIP_DIALOG_DESCRIPTION_ACTION_TEXT.toString(param1["description"],param1["actionText"]);
         _loc3_ = new TutorialDialog();
         var _loc4_:DialogRequest = new DialogRequest(_loc3_,_loc2_);
         _loc4_.modality = DialogModality.GAMEPLAY;
         DialogManager.RequestDialog(_loc4_);
      }
      
      protected function GetDialogFromData(param1:IDialogData) : IDialog
      {
         var _loc2_:DialogContainer = new DialogContainer();
         _loc2_.Header = this.GetHeaderFromData(param1,_loc2_);
         _loc2_.Footer = this.GetFooterFromData(param1);
         return _loc2_;
      }
      
      protected function GetHeaderFromData(param1:IDialogData, param2:DialogContainer) : DialogHeaderCellView
      {
         var _loc3_:TextInputIconSelectHeader = null;
         var _loc4_:TextDialogInput = null;
         if(param1.icon)
         {
            if(Boolean(param1.iconInfos) && Boolean(param1.dialogType == DialogTypes.YES_NO) && param1.inputs.length == 2)
            {
               _loc3_ = new TextInputIconSelectHeader();
               _loc3_.DialogContainer = param2;
               return _loc3_;
            }
            if(param1.dialogType == DialogTypes.ONE_BUTTON_INPUT || param1.dialogType == DialogTypes.TWO_BUTTON_INPUT || param1.dialogType == DialogTypes.YES && param1.inputs.length == 1 || param1.dialogType == DialogTypes.YES_NO && param1.inputs.length == 1)
            {
               if(param1.inputs[0].inputType == DialogInputType.DROPDOWN)
               {
               }
               return new TextInputImageHeader();
            }
            return new TitleBodyImageHeader();
         }
         if(param1.inputs.length == 0)
         {
            return new TitleBodyHeader();
         }
         if(param1.dialogType == DialogTypes.ONE_BUTTON_TWO_INPUT || param1.dialogType == DialogTypes.YES && param1.inputs.length == 2 || param1.dialogType == DialogTypes.YES_NO && param1.inputs.length == 2)
         {
            if(param1.inputs[0].inputType == DialogInputType.TEXT && param1.inputs[1].inputType == DialogInputType.TEXT)
            {
               _loc4_ = param1.inputs[1] as TextDialogInput;
               if(_loc4_.heightIncrease < 0)
               {
                  _loc4_.heightIncrease = DialogTunables.VARIABLE_INPUT_TWO_INPUT_HEIGHT_INCREASE;
               }
            }
         }
         else if(param1.additionalTexts.length == 2)
         {
            _loc4_ = param1.inputs[0] as TextDialogInput;
            _loc4_.inline = true;
            return new PaymentInputHeader();
         }
         return new VariableInputHeader();
      }
      
      protected function GetFooterFromData(param1:IDialogData) : DialogFooterCellView
      {
         if(param1.dialogType == DialogTypes.YES || param1.dialogType == DialogTypes.YES_NO)
         {
            return new YesNoFooter();
         }
         return new DialogButtonFooter();
      }
      
      protected function HandleShowFTUEDialog(param1:Object) : *
      {
         var _loc2_:int = int(param1["type"]);
         switch(_loc2_)
         {
            case SharedTutorialUtils.FTUE_DIALOG_START:
               this.ShowFTUEStartDialog(param1["option1Callback"],param1["option2Callback"],param1["FTUEDisabledCallback"]);
               break;
            case SharedTutorialUtils.FTUE_DIALOG_END:
               this.ShowFTUEEndDialog(param1["option1Callback"],param1["option2Callback"],param1["option3Callback"],param1["contextParams"]);
               break;
            case SharedTutorialUtils.FTUE_DIALOG_ASPIRATION:
               this.ShowFTUEAspirationDialog(param1["option1Callback"]);
         }
      }
      
      protected function ShowFTUEStartDialog(param1:Function, param2:Function, param3:Function) : void
      {
         var _loc5_:LocalCheckBoxRequestData = null;
         var _loc6_:IconInfo = null;
         var _loc7_:IconInfo = null;
         var _loc8_:DialogContainer = null;
         var _loc9_:DialogRequest = null;
         var _loc4_:Boolean = Boolean(CommunicationManager.CallGameService("OptionsGetValue",{"name":"EnableFTUETutorialStart"}));
         if(_loc4_)
         {
            _loc5_ = new LocalCheckBoxRequestData();
            _loc5_.dialog_id = "FTUEDialogStart";
            _loc5_.title = Keys.TUTORIAL_FTUE_START_DIALOG_TITLE.toString();
            _loc5_.checkboxLabel = Keys.TUTORIAL_FTUE_START_DIALOG_DO_NOT_ASK.toString();
            _loc5_.settingName = "EnableFTUETutorialStart";
            _loc5_.checkboxDefaultValue = false;
            _loc5_.bSettingIsOption = true;
            _loc5_.bNegateValue = true;
            _loc6_ = new IconInfo({
               "name":Keys.TUTORIAL_FTUE_START_DIALOG_OPTION1_SUBTITLE,
               "desc":Keys.TUTORIAL_FTUE_START_DIALOG_OPTION1_DESC,
               "icon":SharedTutorialUtils.IMAGE_FTUE_NEW_GAME_DIALOG_SKIP
            });
            _loc7_ = new IconInfo({
               "name":Keys.TUTORIAL_FTUE_START_DIALOG_OPTION2_SUBTITLE,
               "desc":Keys.TUTORIAL_FTUE_START_DIALOG_OPTION2_DESC,
               "icon":SharedTutorialUtils.IMAGE_FTUE_NEW_GAME_DIALOG_PLAY
            });
            _loc5_.actions.push(new CallbackDialogAction(param1,null,Keys.TUTORIAL_FTUE_START_DIALOG_OPTION1_TITLE.toString(),true,null,null,_loc6_));
            _loc5_.actions.push(new CallbackDialogAction(param2,null,Keys.TUTORIAL_FTUE_START_DIALOG_OPTION2_TITLE.toString(),true,null,null,_loc7_));
            _loc8_ = new DialogContainer();
            _loc8_.Header = new GridIconButtonsHeader(getDefinitionByName("widgets.Dialog.controls.DialogIconActionButtonFtueStart") as Class,false,1);
            _loc8_.Footer = new CheckBoxConfirmFooter(true);
            _loc9_ = new DialogRequest(_loc8_,_loc5_);
            _loc9_.modality = DialogModality.GAMEPLAY;
            DialogManager.RequestDialog(_loc9_);
         }
         else
         {
            param3();
         }
      }
      
      protected function ShowFTUEEndDialog(param1:Function, param2:Function, param3:Function, param4:Object) : void
      {
         var _loc5_:LocalRequestData = null;
         var _loc9_:DialogContainer = null;
         _loc5_ = new LocalRequestData();
         _loc5_.dialog_id = "FTUEDialogEnd";
         _loc5_.title = Keys.TUTORIAL_FTUE_END_DIALOG_TITLE.toString();
         _loc5_.options = GenericDialogOption.DISABLE_CLOSE_BUTTON;
         var _loc6_:IconInfo = new IconInfo({
            "desc":Keys.TUTORIAL_FTUE_END_DIALOG_OPTION1_DESC,
            "icon":SharedTutorialUtils.IMAGE_FTUE_END_GAME_DIALOG_ADDSIM
         });
         var _loc7_:IconInfo = new IconInfo({
            "desc":Keys.TUTORIAL_FTUE_END_DIALOG_OPTION2_DESC,
            "icon":SharedTutorialUtils.IMAGE_FTUE_END_GAME_DIALOG_CONTINUE
         });
         var _loc8_:IconInfo = new IconInfo({
            "desc":Keys.TUTORIAL_FTUE_END_DIALOG_OPTION3_DESC,
            "icon":SharedTutorialUtils.IMAGE_FTUE_END_GAME_DIALOG_NEWGAME
         });
         _loc5_.actions.push(new CallbackDialogAction(param1,param4,Keys.TUTORIAL_FTUE_END_DIALOG_OPTION1_TITLE.toString(),true,null,null,_loc6_));
         _loc5_.actions.push(new CallbackDialogAction(param2,param4,Keys.TUTORIAL_FTUE_END_DIALOG_OPTION2_TITLE.toString(),true,null,null,_loc7_));
         _loc5_.actions.push(new CallbackDialogAction(param3,param4,Keys.TUTORIAL_FTUE_END_DIALOG_OPTION3_TITLE.toString(),true,null,null,_loc8_));
         _loc9_ = new DialogContainer();
         _loc9_.Header = new GridIconButtonsHeader(getDefinitionByName("widgets.Dialog.controls.DialogIconActionButtonFtueEnd") as Class,false,0);
         _loc9_.Footer = new CheckBoxConfirmFooter(true);
         var _loc10_:DialogRequest = new DialogRequest(_loc9_,_loc5_);
         _loc10_.modality = DialogModality.GAMEPLAY;
         DialogManager.RequestDialog(_loc10_);
      }
      
      protected function ShowFTUEAspirationDialog(param1:Function) : void
      {
         var _loc2_:LocalRequestData = null;
         var _loc10_:DialogContainer = null;
         _loc2_ = new LocalRequestData();
         _loc2_.dialog_id = "FTUEDialogEnd";
         _loc2_.title = Keys.TUTORIAL_FTUE_ASPIRATION_DIALOG_TITLE.toString();
         _loc2_.promptText = Keys.TUTORIAL_FTUE_ASPIRATION_DIALOG_SUB_TITLE.toString();
         _loc2_.options = GenericDialogOption.DISABLE_CLOSE_BUTTON;
         var _loc3_:String = SharedTutorialUtils.GetFTUEPlayerSimId();
         var _loc4_:IconInfo = new IconInfo({
            "name":Keys.TUTORIAL_FTUE_ASPIRATION_DIALOG_OPTION1_SUBTITLE,
            "desc":Keys.TUTORIAL_FTUE_ASPIRATION_DIALOG_OPTION1_DESC,
            "icon":SharedTutorialUtils.IMAGE_FTUE_ASPIRATION_DIALOG_CAREER,
            "object_instance_id":_loc3_
         });
         var _loc5_:IconInfo = new IconInfo({
            "name":Keys.TUTORIAL_FTUE_ASPIRATION_DIALOG_OPTION2_SUBTITLE,
            "desc":Keys.TUTORIAL_FTUE_ASPIRATION_DIALOG_OPTION2_DESC,
            "icon":SharedTutorialUtils.IMAGE_FTUE_ASPIRATION_DIALOG_ROMANTIC,
            "object_instance_id":_loc3_
         });
         var _loc6_:IconInfo = new IconInfo({
            "name":Keys.TUTORIAL_FTUE_ASPIRATION_DIALOG_OPTION3_SUBTITLE,
            "desc":Keys.TUTORIAL_FTUE_ASPIRATION_DIALOG_OPTION3_DESC,
            "icon":SharedTutorialUtils.IMAGE_FTUE_ASPIRATION_DIALOG_ARCHITECT,
            "object_instance_id":_loc3_
         });
         var _loc7_:IconInfo = new IconInfo({
            "name":Keys.TUTORIAL_FTUE_ASPIRATION_DIALOG_OPTION4_SUBTITLE,
            "desc":Keys.TUTORIAL_FTUE_ASPIRATION_DIALOG_OPTION4_DESC,
            "icon":SharedTutorialUtils.IMAGE_FTUE_ASPIRATION_DIALOG_DEVIOUS,
            "object_instance_id":_loc3_
         });
         var _loc8_:Object = {"simId":_loc3_};
         var _loc9_:Object = {
            "aspiration_id":SharedTutorialUtils.INSTANCE_FTUE_ASPIRATION_1,
            "tooltipType":AspirationTooltip,
            "tooltipData":AspirationTooltip.GetAspirationTooltipData(SharedTutorialUtils.INSTANCE_FTUE_ASPIRATION_1)
         };
         _loc2_.actions.push(new CallbackDialogAction(param1,_loc9_,Keys.TUTORIAL_FTUE_ASPIRATION_DIALOG_OPTION1_TITLE.toString(_loc8_),true,null,null,_loc4_));
         _loc9_ = {
            "aspiration_id":SharedTutorialUtils.INSTANCE_FTUE_ASPIRATION_2,
            "tooltipType":AspirationTooltip,
            "tooltipData":AspirationTooltip.GetAspirationTooltipData(SharedTutorialUtils.INSTANCE_FTUE_ASPIRATION_2)
         };
         _loc2_.actions.push(new CallbackDialogAction(param1,_loc9_,Keys.TUTORIAL_FTUE_ASPIRATION_DIALOG_OPTION2_TITLE.toString(_loc8_),true,null,null,_loc5_));
         _loc9_ = {
            "aspiration_id":SharedTutorialUtils.INSTANCE_FTUE_ASPIRATION_3,
            "tooltipType":AspirationTooltip,
            "tooltipData":AspirationTooltip.GetAspirationTooltipData(SharedTutorialUtils.INSTANCE_FTUE_ASPIRATION_3)
         };
         _loc2_.actions.push(new CallbackDialogAction(param1,_loc9_,Keys.TUTORIAL_FTUE_ASPIRATION_DIALOG_OPTION3_TITLE.toString(_loc8_),true,null,null,_loc6_));
         _loc9_ = {
            "aspiration_id":SharedTutorialUtils.INSTANCE_FTUE_ASPIRATION_4,
            "tooltipType":AspirationTooltip,
            "tooltipData":AspirationTooltip.GetAspirationTooltipData(SharedTutorialUtils.INSTANCE_FTUE_ASPIRATION_4)
         };
         _loc2_.actions.push(new CallbackDialogAction(param1,_loc9_,Keys.TUTORIAL_FTUE_ASPIRATION_DIALOG_OPTION4_TITLE.toString(_loc8_),true,null,null,_loc7_));
         _loc10_ = new DialogContainer();
         _loc10_.Header = new GridIconButtonsHeader(getDefinitionByName("widgets.Dialog.controls.DialogIconActionButtonFtueAspiration") as Class,false);
         _loc10_.Footer = new CheckBoxConfirmFooter(true);
         var _loc11_:DialogRequest = new DialogRequest(_loc10_,_loc2_);
         _loc11_.modality = DialogModality.GAMEPLAY;
         DialogManager.RequestDialog(_loc11_);
      }
      
      protected function ShowCDSContentInstalledDialog(param1:Object) : void
      {
         CommunicationManager.CallGameService("ShowCDSContentInstalledDialogWithTelemetry",param1);
      }
      
      protected function ShowCDSContentInstalledDialogWithTelemetry(param1:Object) : void
      {
         var args:Object = param1;
         var restart:Function = function(param1:Object):void
         {
            var _loc2_:Object = null;
            if(param1 != null && param1["telemetry"] != null)
            {
               _loc2_ = param1["telemetry"]["attributes"] as Object;
               if(_loc2_)
               {
                  _loc2_["rstr"] = 1;
               }
               TelemetryManager.DispatchTelemetryEventObject(param1["telemetry"]);
            }
            if(SystemUtils.IsConsole)
            {
               CommunicationManager.SendMessage("RestartConfirmed");
            }
            else
            {
               CommunicationManager.CallUIService("ConfirmRestart");
            }
         };
         var cancel:Function = function(param1:Object):void
         {
            var _loc2_:Object = null;
            if(param1 != null && param1["telemetry"] != null)
            {
               _loc2_ = param1["telemetry"]["attributes"] as Object;
               if(_loc2_)
               {
                  _loc2_["rstr"] = 0;
               }
               TelemetryManager.DispatchTelemetryEventObject(param1["telemetry"]);
            }
         };
         var dialog:Object = {
            "type":DialogTypes.TWO_BUTTON,
            "title":Keys.CDS_DIALOG_NEW_CONTENT_TITLE.toString(),
            "description":Keys.CDS_DIALOG_NEW_CONTENT_DESCRIPTION.toString(),
            "optionOneText":Keys.CDS_DIALOG_NEW_CONTENT_CONFIRM.toString(),
            "optionTwoText":Keys.CDS_DIALOG_NEW_CONTENT_CANCEL.toString(),
            "optionOneAudio":"OKButton",
            "optionTwoAudio":"CancelButton",
            "options":GenericDialogOption.DISABLE_CLOSE_BUTTON,
            "optionOneCallback":restart,
            "optionOneParams":args,
            "optionTwoCallback":cancel,
            "optionTwoParams":args,
            "modality":DialogModality.GAMEPLAY,
            "widgetName":WidgetUtils.GetBaseName(this)
         };
         CommunicationManager.SendUIMessage("ShowDialog",dialog);
      }
      
      public function TriggerDownloadCompleteDialog(param1:Object) : void
      {
         var downloadState:int;
         var bundleDesc:String = null;
         var returnToMainMenu:Function = null;
         var showDownloadComplete:Function = null;
         var downloadManagerData:Object = null;
         var dataArray:Array = null;
         var bBundleFound:Boolean = false;
         var index:int = 0;
         var args:Object = param1;
         bundleDesc = "";
         returnToMainMenu = function(param1:Object):void
         {
            CommunicationManager.SendUIMessage("ShowExitToMainMenuDialog");
         };
         showDownloadComplete = function(param1:Object):void
         {
            mDownloadCompleteDelayTimer.removeEventListener(TimerEvent.TIMER_COMPLETE,showDownloadComplete);
            mDownloadCompleteDelayTimer = null;
            var _loc2_:Object = {
               "type":DialogTypes.TWO_BUTTON,
               "title":Keys.DOWNLOAD_COMPLETE_DIALOG_TITLE.toString(),
               "description":bundleDesc,
               "optionOneText":Keys.GENERIC_YES.toString(),
               "optionTwoText":Keys.GENERIC_NO.toString(),
               "optionOneAudio":"OKButton",
               "optionTwoAudio":"CancelButton",
               "options":GenericDialogOption.PAUSE_WHEN_DIALOG_UP_IN_SINGLE_PLAYER | GenericDialogOption.VERTICAL_NOTIFICATION_BUTTONS,
               "optionOneCallback":returnToMainMenu,
               "modality":DialogModality.SYSTEM
            };
            CommunicationManager.SendUIMessage("ShowDialog",_loc2_);
         };
         var gameState:uint = CommunicationManager.CallGameService("GetGameState") as uint;
         if(gameState == GameStates.MAIN_MENU)
         {
            return;
         }
         if(args == null)
         {
            return;
         }
         downloadState = int(args["downloadState"]);
         if(downloadState != DownloadSharedTunables.DOWNLOAD_STATE_FINISHED)
         {
            return;
         }
         if(this.mDownloadCompleteDelayTimer)
         {
            this.mDownloadCompleteDelayTimer.stop();
            bundleDesc = Keys.DOWNLOAD_COMPLETE_DIALOG_DESCRIPTION_MULTI.toString();
            this.mDownloadCompleteDelayTimer = new Timer(DialogTunables.DOWNLOAD_COMPLETE_NOTIFICATION_DIALOG_TIMER);
            this.mDownloadCompleteDelayTimer.addEventListener(TimerEvent.TIMER_COMPLETE,showDownloadComplete,false,0,true);
         }
         else
         {
            if(!args.hasOwnProperty("bundleId"))
            {
               return;
            }
            downloadManagerData = CommunicationManager.CallGameService("RequestDownloadManagerData");
            if(downloadManagerData == null || !downloadManagerData.hasOwnProperty("downloads"))
            {
               return;
            }
            dataArray = downloadManagerData["downloads"] as Array;
            if(dataArray == null || dataArray.length == 0)
            {
               return;
            }
            bBundleFound = false;
            index = 0;
            while(index < dataArray.length)
            {
               if(dataArray[index].bundleId == args["bundleId"])
               {
                  bundleDesc = Keys.DOWNLOAD_COMPLETE_DIALOG_DESCRIPTION_SINGLE.toString(dataArray[index].name);
                  bBundleFound = true;
                  break;
               }
               index++;
            }
            if(!bBundleFound)
            {
               return;
            }
            this.mDownloadCompleteDelayTimer = new Timer(DialogTunables.DOWNLOAD_COMPLETE_NOTIFICATION_DIALOG_TIMER);
            this.mDownloadCompleteDelayTimer.addEventListener(TimerEvent.TIMER_COMPLETE,showDownloadComplete,false,0,true);
         }
         this.mDownloadCompleteDelayTimer.start();
      }
      
      protected function InitGamepad() : void
      {
         this.mDynamicOmniInputAdapter = new DynamicOmniPointAdapter(this);
         this.mDynamicOmniInputAdapter.SetHighlightClosestOnEnter(true);
         this.mDynamicOmniInputAdapter.ElementShouldBeAddedCheck = ElementShouldBeAdded;
         this.mDynamicOmniInputAdapter.IncludeObjectsWithTooltips();
         this.mDynamicOmniInputAdapter.UseWideAngle();
         this.mDynamicOmniInputAdapter.SetAllowedDuringLoadingScreen(true);
         this.mDynamicOmniInputAdapter.OnConfirmCall(this.HandleConfirmEvent);
         this.mDynamicOmniInputAdapter.OnBackCall(DialogManager.HandleEscapeKey);
         this.mDynamicOmniInputAdapter.SetupDefaultVirtualKeyboardParams(this.OnVKeyboardOutput);
         var _loc1_:InputAction = InputAction.WhenTriggered(InputTrigger.FromActionCode(ActionCodes.TRIGGER_RIGHT)).CallFunction(DialogManager.HandleOKConfirm).AllowWhileModalOpen();
         this.mDynamicOmniInputAdapter.AddInputAction(_loc1_);
         CommunicationManager.AddMessageListener("UsingControllerToggled",this.HandleUsingControllerToggled,this);
      }
      
      protected function HandleConfirmEvent(param1:InputAdapterConfirmEvent) : void
      {
         var _loc3_:TextInput = null;
         var _loc4_:EditTextField = null;
         var _loc2_:DisplayObject = param1.GetObj() as DisplayObject;
         if(_loc2_ is TextInput)
         {
            _loc3_ = _loc2_ as TextInput;
            _loc3_.focused = 1;
         }
         else if(_loc2_ is EditTextField)
         {
            _loc4_ = _loc2_ as EditTextField;
            _loc4_.StartEdit(null);
         }
      }
      
      protected function OnVKeyboardOutput(param1:Object, param2:uint, param3:String) : void
      {
         if(param1 is TextInput)
         {
            this.OnVKeyboardOutputTextInput(param1 as TextInput,param2,param3);
         }
         else if(param1 is EditTextField)
         {
            this.OnVKeyboardOutputEditTextField(param1 as EditTextField,param2,param3);
         }
      }
      
      protected function OnVKeyboardOutputTextInput(param1:TextInput, param2:uint, param3:String) : void
      {
         var _loc5_:DialogRequest = null;
         var _loc6_:DialogContainer = null;
         var _loc4_:int = 0;
         if(Boolean(param1) && param2 == VirtualKeyboardHelper.STATUS_COMPLETE)
         {
            param1.text = param3;
            _loc5_ = DialogManager.GetCurrentRequest();
            if(_loc5_)
            {
               if(_loc5_.data.inputs.length > 0)
               {
                  _loc6_ = _loc5_.dialog as DialogContainer;
                  if(_loc6_)
                  {
                     _loc5_.data.inputs[_loc4_].value = param3;
                     _loc6_.mcHeader.CheckValidity();
                  }
               }
            }
         }
      }
      
      protected function OnVKeyboardOutputEditTextField(param1:EditTextField, param2:uint, param3:String) : void
      {
         if(Boolean(param1) && param2 == VirtualKeyboardHelper.STATUS_COMPLETE)
         {
            param1.SetTextFromVKeyboard(param3);
         }
      }
      
      protected function HandleTransitionScreenHideComplete() : void
      {
         RemoveMessageListener("TransitionCompleteDialogProcessed",this.HandleTransitionScreenHideComplete);
         if(NavManager.Instance.CurrentFocusable == this)
         {
            this.mDynamicOmniInputAdapter.UpdateElements();
            this.mDynamicOmniInputAdapter.SetHighlightedObject(this.mDynamicOmniInputAdapter.GetHighlightedObject(),true);
         }
      }
      
      protected function HandleUsingControllerToggled() : void
      {
         var _loc2_:TextInput = null;
         var _loc1_:int = 0;
         while(_loc1_ < this.mDynamicOmniInputAdapter.GetLength())
         {
            _loc2_ = this.mDynamicOmniInputAdapter.GetElementAt(_loc1_) as TextInput;
            if(_loc2_ != null)
            {
               _loc2_.focused = 0;
            }
            _loc1_++;
         }
      }
      
      override public function Enter(param1:EnterParams = null) : IInputFocusable
      {
         var _loc4_:IInputAdapter = null;
         var _loc5_:DialogContainer = null;
         var _loc6_:IInputAdapter = null;
         var _loc2_:Boolean = Boolean(CommunicationManager.CallUIService("IsTransitionScreenVisible"));
         if(_loc2_)
         {
            AddMessageListener("TransitionCompleteDialogProcessed",this.HandleTransitionScreenHideComplete);
         }
         if(!param1)
         {
            param1 = new EnterParams();
         }
         param1.mFromPos = new Point(stage.stageWidth,stage.stageHeight);
         this.mCurrentDialogInputFocusStack = [];
         var _loc3_:DialogRequest = DialogManager.GetCurrentRequest();
         if(Boolean(_loc3_) && _loc3_.dialog is IInputAdapter)
         {
            _loc4_ = _loc3_.dialog as IInputAdapter;
            _loc4_.OnInputEventCall(InputAdapterEvent.CONFIRM,this.HandleConfirmEvent);
            _loc4_.OnInputEventCall(InputAdapterEvent.BACK,DialogManager.HandleEscapeKey);
            this.mCurrentDialogInputFocusStack.push(_loc4_.Enter(param1));
            this.bUseThisForFocusBack = false;
         }
         else
         {
            if(Boolean(_loc3_) && _loc3_.dialog is DialogContainer)
            {
               _loc5_ = _loc3_.dialog as DialogContainer;
               if((Boolean(_loc5_)) && Boolean(_loc5_.mcHeader))
               {
                  if(_loc5_.mcHeader is IInputAdapter)
                  {
                     _loc6_ = _loc5_.mcHeader as IInputAdapter;
                     this.mCurrentDialogInputFocusStack.push(_loc6_.Enter(param1));
                  }
               }
            }
            this.mCurrentDialogInputFocusStack.push(this.mDynamicOmniInputAdapter.Enter(param1));
            this.bUseThisForFocusBack = true;
         }
         return this.bUseThisForFocusBack ? this : this.mCurrentDialogInputFocusStack[0];
      }
      
      override public function Exit() : void
      {
         var _loc1_:IInputFocusable = null;
         for each(_loc1_ in this.mCurrentDialogInputFocusStack)
         {
            _loc1_.Exit();
         }
         this.mCurrentDialogInputFocusStack = [];
      }
   }
}

