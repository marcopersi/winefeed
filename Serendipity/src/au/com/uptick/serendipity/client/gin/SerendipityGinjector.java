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

package au.com.uptick.serendipity.client.gin;

import com.google.gwt.event.shared.EventBus;
import com.google.gwt.inject.client.AsyncProvider;
import com.google.gwt.inject.client.GinModules;
import com.google.gwt.inject.client.Ginjector;

import com.google.inject.Provider;

import com.gwtplatform.dispatch.client.gin.DispatchAsyncModule;
import com.gwtplatform.mvp.client.proxy.PlaceManager;
import com.gwtplatform.mvp.client.proxy.ProxyFailureHandler;

import au.com.uptick.serendipity.client.AdminGatekeeper;
import au.com.uptick.serendipity.client.LoggedInGatekeeper;
import au.com.uptick.serendipity.client.presenter.ErrorPagePresenter;
import au.com.uptick.serendipity.client.presenter.MainPagePresenter;
import au.com.uptick.serendipity.client.presenter.SignInPagePresenter;
import au.com.uptick.serendipity.client.resourcecentre.presenter.HighlightsPresenter;
import au.com.uptick.serendipity.client.sales.account.presenter.AccountInformationPresenter;
import au.com.uptick.serendipity.client.sales.account.presenter.AccountPagePresenter;
import au.com.uptick.serendipity.client.sales.account.presenter.FileUploadPagePresenter;
import au.com.uptick.serendipity.client.sales.presenter.AccountsPresenter;
import au.com.uptick.serendipity.client.sales.presenter.ActivitiesPresenter;
import au.com.uptick.serendipity.client.sales.presenter.CalendarPresenter;
import au.com.uptick.serendipity.client.sales.presenter.DashboardsPresenter;
import au.com.uptick.serendipity.client.sales.presenter.ImportsPresenter;
import au.com.uptick.serendipity.client.sales.presenter.ReportsPresenter;
import au.com.uptick.serendipity.client.settings.presenter.AdministrationPresenter;

@GinModules({DispatchAsyncModule.class, ClientModule.class})
public interface SerendipityGinjector extends Ginjector {

  EventBus getEventBus();
  PlaceManager getPlaceManager();
  // Resources getResources();
  // DispatchAsync getDispatcher();
  // ProxyFailureHandler getProxyFailureHandler();
  // CurrentUser getCurrentUser();
  // Translations getTranslations();

  LoggedInGatekeeper getLoggedInGatekeeper();
  AdminGatekeeper    getAdminGatekeeper();

  // Sign In
  Provider<SignInPagePresenter> getSignInPagePresenter();

  // Main Page(s)
  AsyncProvider<MainPagePresenter> getMainPagePresenter();

  Provider<AccountPagePresenter> getAccountPagePresenter();
  Provider<FileUploadPagePresenter> getFileUploadPagePresenter();

  // Error Page
  AsyncProvider<ErrorPagePresenter> getErrorPagePresenter();

  // Sales
  AsyncProvider<ActivitiesPresenter> getActivitiesPresenter();
  AsyncProvider<CalendarPresenter> getCalendarPresenter();
  AsyncProvider<DashboardsPresenter> getDashboardsPresenter();
  AsyncProvider<ImportsPresenter> getImportsPresenter();
  AsyncProvider<AccountsPresenter> getAccountsPresenter();
  AsyncProvider<ReportsPresenter> getReportsPresenter();

  AsyncProvider<AccountInformationPresenter> getAccountInformationPresenter();

  // Settings
  AsyncProvider<AdministrationPresenter> getAdministrationPresenter();

  // Resource Centre
  AsyncProvider<HighlightsPresenter> getHighlightsPresenter();

  ProxyFailureHandler getProxyFailureHandler();
}
