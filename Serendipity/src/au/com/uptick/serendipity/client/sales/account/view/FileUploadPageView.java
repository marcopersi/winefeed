/**
 * (C) Copyright 2010, 2011 upTick Pty Ltd
 *
 * Licensed under the terms of the GNU General Public License version 3
 * as published by the Free Software Foundation. You may obtain a copy of the
 * License at: http://www.gnu.org/copyleft/gpl.html
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
 * WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
 * License for the specific language governing permissions and limitations
 * under the License.
 */

package au.com.uptick.serendipity.client.sales.account.view;

import au.com.uptick.serendipity.client.FileUploadEntryPoint;
import au.com.uptick.serendipity.client.sales.account.presenter.FileUploadPagePresenter;
import au.com.uptick.serendipity.client.sales.account.view.handlers.FileUploadUiHandlers;

import com.allen_sauer.gwt.log.client.Log;
import com.google.gwt.user.client.Window;
import com.google.gwt.user.client.ui.NamedFrame;
import com.google.gwt.user.client.ui.Widget;
import com.google.inject.Inject;
import com.gwtplatform.mvp.client.ViewWithUiHandlers;
import com.smartgwt.client.types.Encoding;
import com.smartgwt.client.types.FormMethod;
import com.smartgwt.client.util.SC;
import com.smartgwt.client.widgets.IButton;
import com.smartgwt.client.widgets.Label;
import com.smartgwt.client.widgets.events.ClickEvent;
import com.smartgwt.client.widgets.events.ClickHandler;
import com.smartgwt.client.widgets.form.DynamicForm;
import com.smartgwt.client.widgets.form.fields.ComboBoxItem;
import com.smartgwt.client.widgets.form.fields.UploadItem;
import com.smartgwt.client.widgets.layout.HLayout;
import com.smartgwt.client.widgets.layout.LayoutSpacer;
import com.smartgwt.client.widgets.layout.VLayout;

public class FileUploadPageView extends ViewWithUiHandlers<FileUploadUiHandlers> implements
    FileUploadPagePresenter.MyView {

  private static final String DEFAULT_MARGIN = "0px";

  private VLayout panel;
  private VLayout northLayout;
  private VLayout southLayout;

  private DynamicForm uploadForm;
  private UploadItem uploadItem;
  private ComboBoxItem recordType;
  private ComboBoxItem mapName;

  @Inject
  public FileUploadPageView() {

    // get rid of scroll bars, and clear out the window's built-in margin,
    // because we want to take advantage of the entire client area
    Window.enableScrolling(false);
    Window.setMargin(DEFAULT_MARGIN);

    // initialise the main layout container
    panel = new VLayout();
    panel.setWidth100();
    panel.setHeight100();

    // panel.setStyleName("crm-Entity-MainLayout");

    // initialise the North layout container
    northLayout = new VLayout();
    northLayout.setWidth100();
    northLayout.setHeight(HEADER_HEIGHT);

    // initialise the South layout container
    southLayout = new VLayout();
    southLayout.setWidth100();
    southLayout.setHeight100();

    // add the nested layout containers to the main layout containers
    northLayout.addMember(initHeader());
    southLayout.addMember(initBody());
    southLayout.addMember(initFooter());

    // add the North and South layout containers to the main layout container
    panel.addMember(northLayout);
    panel.addMember(southLayout);

    // bindCustomUiHandlers();

    // set the browser window's title
    Window.setTitle("Upload Data File");
  }

  protected void bindCustomUiHandlers() { }

  @Override
  public Widget asWidget() {
    return panel;
  }

  private static final int HEADER_HEIGHT = 58;
  private static final String NAME = "Select a Data File to Upload";
  private static final String DESCRIPTION = "Select a data file to be imported into Serendipity.";

  private VLayout initHeader() {

    // initialise the Header layout container
    VLayout header = new VLayout();
    header.setStyleName("crm-Wizard-Header");
    header.setWidth100();
    header.setHeight(HEADER_HEIGHT);

    HLayout line1 = new HLayout();
    line1.setWidth100();
    line1.setHeight100();

    HLayout line2 = new HLayout();
    line2.setWidth100();
    line2.setHeight100();

    // initialise the Name label
    Label name = new Label();
    name.setStyleName("crm-Wizard-Name");
    name.setContents(NAME);
    name.setWidth100();

    // initialise the Description label
    Label description = new Label();
    description.setStyleName("crm-Wizard-Description");
    description.setContents(DESCRIPTION);
    description.setWidth100();

    // add the labels to the nested layout containers
    line1.addMember(name);
    line2.addMember(description);

    // add the North and South layout containers to the main layout container
    header.addMember(line1);
    header.addMember(line2);

    return header;
  }

  private static final String DEFAULT_FILE_UPLOAD_SERVICE_PATH = "upload";
  private static final String RECORD_TYPE = "recordType";
  private static final String MAP_NAME = "mapName";
  private static final String TARGET = "uploadTarget";

  private VLayout initBody() {

    // initialise the Footer layout container
    VLayout body = new VLayout();
    body.setStyleName("crm-Wizard-Body");
    body.setWidth100();
    body.setHeight100();

    // initialise the form
    uploadForm = new DynamicForm();
    uploadForm.setWidth100();
    uploadForm.setMargin(8);
    uploadForm.setNumCols(2);
    uploadForm.setCellPadding(2);
    // uploadForm.setAutoFocus(false);
    uploadForm.setWrapItemTitles(false);
    // no ":" after the field name
    uploadForm.setTitleSuffix(" ");
    uploadForm.setRequiredTitleSuffix(" ");

    // initialise the hidden frame
    NamedFrame frame = new NamedFrame(TARGET);
    frame.setWidth("1px");
    frame.setHeight("1px");
    frame.setVisible(false);

    uploadForm.setEncoding(Encoding.MULTIPART);
    uploadForm.setMethod(FormMethod.POST);
    // set the (hidden) form target
    uploadForm.setTarget(TARGET);

    StringBuilder url = new StringBuilder();
    url.append(DEFAULT_FILE_UPLOAD_SERVICE_PATH);
    uploadForm.setAction(FileUploadEntryPoint.getRelativeURL(url.toString()));

    // initialise the Record type field
    recordType = new ComboBoxItem(RECORD_TYPE, "Record type");
    recordType.setName(RECORD_TYPE);
    recordType.setType("comboBox");
    recordType.setValueMap("Account", "Contact");
    recordType.setDefaultToFirstOption(true);
    recordType.setSelectOnFocus(true);

    // initialise the Map field
    mapName = new ComboBoxItem(MAP_NAME, "Data map");
    mapName.setName(MAP_NAME);
    mapName.setType("comboBox");
    mapName.setValueMap("Automatic", "Create new map");
    mapName.setDefaultToFirstOption(true);

    // initialise the File name field
    uploadItem = new UploadItem("filename");
    uploadItem.setName("filename");
    uploadItem.setTitle("File name");
    uploadItem.setWidth(280);

    // set the fields into the form
    uploadForm.setFields(recordType, mapName, uploadItem);

    // add the Upload Form and the (hidden) Frame to the main layout container
    body.addMember(uploadForm);
    body.addMember(frame);

    return body;
  }

  private static final int FOOTER_HEIGHT = 48;

  private VLayout initFooter() {

    // initialise the Footer layout container
    VLayout footer = new VLayout();
    footer.setStyleName("crm-Wizard-Footer");
    footer.setWidth100();
    footer.setHeight(FOOTER_HEIGHT);

    HLayout hLayout = new HLayout();
    hLayout.setWidth100();
    hLayout.setHeight(FOOTER_HEIGHT);

    // initialise the OK button
    IButton okButton = new IButton("OK");
    // stretchButton.setWidth(150);
    okButton.setShowRollOver(true);
    okButton.setShowDisabled(true);
    okButton.setShowDown(true);
    // stretchButton.setTitleStyle("stretchTitle");
    // stretchButton.setIcon("silk/printer.png");
    okButton.addClickHandler(new ClickHandler() {
        public void onClick(ClickEvent event) {
            Object obj = uploadItem.getDisplayValue();
            if (obj != null) {

              Log.debug("uploadItem.getDisplayValue()" + obj.toString());

              uploadForm.submitForm();
              if (getUiHandlers() != null) {
                getUiHandlers().onOkButtonClicked();
              }
            } else {
              SC.say("Please select a file.");
          }
      }
    });

    // initialise the Cancel button
    IButton cancelButton = new IButton("Cancel");
    cancelButton.setShowRollOver(true);
    cancelButton.setShowDisabled(true);
    cancelButton.setShowDown(true);
    cancelButton.addClickHandler(new ClickHandler() {
        public void onClick(ClickEvent event) {
      if (getUiHandlers() != null) {
        getUiHandlers().onCancelButtonClicked();
      }
    }});

    // layout the OK and Cancel buttons
    hLayout.setLayoutMargin(8);
    hLayout.addMember(new LayoutSpacer());
    hLayout.addMember(okButton);
    LayoutSpacer padding = new LayoutSpacer();
    padding.setWidth(8);
    hLayout.addMember(padding);
    hLayout.addMember(cancelButton);

    // add the nested layout container to the main layout container
    footer.addMember(hLayout);

    return footer;
  }
}
