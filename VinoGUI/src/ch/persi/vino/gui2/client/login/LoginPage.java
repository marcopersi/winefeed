package ch.persi.vino.gui2.client.login;

import com.google.gwt.core.client.EntryPoint;
import com.google.gwt.core.shared.GWT;
import com.google.gwt.user.client.Window;
import com.google.gwt.user.client.ui.HTMLPanel;
import com.google.gwt.user.client.ui.PasswordTextBox;
import com.google.gwt.user.client.ui.RootPanel;
import com.google.gwt.user.client.ui.TextBox;
import com.gwtplatform.mvp.client.annotations.NameToken;
import com.gwtplatform.mvp.client.annotations.NoGatekeeper;
import com.gwtplatform.mvp.client.annotations.ProxyStandard;
import com.smartgwt.client.util.SC;
import com.smartgwt.client.widgets.Button;
import com.smartgwt.client.widgets.events.ClickEvent;
import com.smartgwt.client.widgets.events.ClickHandler;

import ch.persi.vino.gui2.client.Pages;
import ch.persi.vino.gui2.shared.FieldVerifier;


@ProxyStandard
@NameToken(Pages.signInPage)
@NoGatekeeper

public class LoginPage implements EntryPoint {

	  private static final String DEFAULT_USER_NAME = "Administrator";
	  private static final String DEFAULT_PASSWORD = "N0More$ecrets";

	
	private static String html = "<div>\n"
		    + "<table align=\"center\">\n"
		    + "  <tr>\n" + "<td>&nbsp;</td>\n" + "<td>&nbsp;</td>\n" + "</tr>\n"
		    + "  <tr>\n" + "<td>&nbsp;</td>\n" + "<td>&nbsp;</td>\n" + "</tr>\n"
		    + "  <tr>\n" + "<td>&nbsp;</td>\n" + "<td>&nbsp;</td>\n" + "</tr>\n"
		    + "  <tr>\n" + "<td>&nbsp;</td>\n" + "<td>&nbsp;</td>\n" + "</tr>\n"
		    + "  <tr>\n" + "<td>&nbsp;</td>\n" + "<td>&nbsp;</td>\n" + "</tr>\n"
		    + "  <tr>\n"
		    + "    <td colspan=\"2\" style=\"font-weight:bold;\">Sign In <img src=\"images/signin.gif\"/></td>\n"
		    + "  </tr>\n"
		    + "  <tr>\n"
		    + "    <td>User name</td>\n"
		    + "    <td id=\"userNameFieldContainer\"></td>\n"
		    + "  </tr>\n"
		    + "  <tr>\n"
		    + "    <td>Password</td>\n"
		    + "    <td id=\"passwordFieldContainer\"></td>\n"
		    + "  </tr>\n"
		    + "  <tr>\n"
		    + "    <td></td>\n"
		    + "    <td id=\"signInButtonContainer\"></td>\n"
		    + "  </tr>\n"
		    + "  <tr>\n" + "<td>&nbsp;</td>\n" + "<td>&nbsp;</td>\n" + "</tr>\n"
		    + "  <tr>\n"
		    + "    <td colspan=\"2\">Forget your password?</td>\n"
		    + "  </tr>\n"
		    + "  <tr>\n"
		    + "    <td colspan=\"2\">Contact your system administrator.</td>\n"
		    + "  </tr>\n"
		    + "</table>\n"
		    + "</div>\n";

		  private HTMLPanel panel;

		  private  TextBox userNameField;
		  private  PasswordTextBox passwordField;
		  private  Button signInButton;
	
	
	@Override
	public void onModuleLoad() {
		// TODO Auto-generated method stub

		    
		    panel = new HTMLPanel(html);
		    
		    userNameField = new TextBox();
		    passwordField = new PasswordTextBox();
		    signInButton = new Button("Sign in");

		    userNameField.setText(DEFAULT_USER_NAME);

		    // See FieldVerifier
		    // Passwords must contain at least 8 characters with at least one digit,
		    // one upper case letter, one lower case letter and one special symbol (“@#$%”).
		    passwordField.setText(DEFAULT_PASSWORD);

		    panel.add(userNameField, "userNameFieldContainer");
		    panel.add(passwordField, "passwordFieldContainer");
		    panel.add(signInButton, "signInButtonContainer");

		    bindCustomUiHandlers();
		    RootPanel.get().add(panel);
	}
	protected void bindCustomUiHandlers() {

	    signInButton.addClickHandler(new ClickHandler() {
	      @Override
	      public void onClick(ClickEvent event) {

	    	  GWT.log("running clickhandler !");
	        if (FieldVerifier.isValidUserName(getUserName()) &&
	           (FieldVerifier.isValidPassword(getPassword()))) {

//	        	PlaceRequest placeRequest = new PlaceRequest(Pages.bidPage);
//	        	// TODO: check if the placemanager story still is the most appropriate way to navigate within GWT GUI
//	            getPlaceManager().revealPlace(placeRequest);
	            Window.open("http://www.blick.ch", "biding page", "");
	        }
	        else {
	          event.cancel();
//	          getView().resetAndFocus();
	          SC.say("Sign in", "You must enter a valid User name and Password.");
	          resetAndFocus();
	        }
	      }
	    });
	  }

	public String getUserName() {
	    return userNameField.getText();
	  }

	  public String getPassword() {
	    return passwordField.getText();
	  }

	  public void resetAndFocus() {
	    userNameField.setFocus(true);
	    userNameField.selectAll();
	  }
}
