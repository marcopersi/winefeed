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

package au.com.uptick.serendipity.client;

public class NameTokens {

  // Main pages
  // public static final String signInPage = "!signInPage";
  public static final String signInPage = "SignInPage";
  public static final String mainPage = "MainPage";
  public static final String errorPage = "ErrorPage";

  public static final String accountPage = "AccountPage";
  public static final String fileUploadPage = "FileUploadPage";

  // Sales nested presenters and views
  public static final String activities = "Activities";
  public static final String calendar = "Calendar";
  public static final String dashboards = "Dashboards";
  public static final String imports = "Imports";
  public static final String leads = "Leads";
  public static final String opportunities = "Opportunities";
  public static final String accounts = "Accounts";
  public static final String contacts = "Contacts";
  public static final String reports = "Reports";

  public static final String accountInformation = "Information";

  // Settings nested presenters and views
  public static final String administration = "Administration";
  public static final String templates = "Templates";
  public static final String datamanagement = "Data Management";

  // Resource Centre nested presenters and views
  public static final String highlights = "Highlights";
  public static final String sales = "Sales";
  public static final String settings = "Settings";

  public static String getSignInPage() {
    return signInPage;
  }

  public static String getMainPage() {
    return mainPage;
  }
}