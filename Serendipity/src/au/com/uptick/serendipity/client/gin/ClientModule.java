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

import au.com.uptick.serendipity.client.AdminGatekeeper;
import au.com.uptick.serendipity.client.LoggedInGatekeeper;
import au.com.uptick.serendipity.client.NameTokens;
import au.com.uptick.serendipity.client.SerendipityPlaceManager;
import au.com.uptick.serendipity.client.presenter.ErrorPagePresenter;
import au.com.uptick.serendipity.client.presenter.MainPagePresenter;
import au.com.uptick.serendipity.client.presenter.SignInPagePresenter;
import au.com.uptick.serendipity.client.resourcecentre.presenter.HighlightsPresenter;
import au.com.uptick.serendipity.client.resourcecentre.view.HighlightsView;
import au.com.uptick.serendipity.client.sales.account.presenter.AccountInformationPresenter;
import au.com.uptick.serendipity.client.sales.account.presenter.AccountPagePresenter;
import au.com.uptick.serendipity.client.sales.account.presenter.FileUploadPagePresenter;
import au.com.uptick.serendipity.client.sales.account.view.AccountInformationView;
import au.com.uptick.serendipity.client.sales.account.view.AccountPageView;
import au.com.uptick.serendipity.client.sales.account.view.FileUploadPageView;
import au.com.uptick.serendipity.client.sales.presenter.AccountsPresenter;
import au.com.uptick.serendipity.client.sales.presenter.ActivitiesPresenter;
import au.com.uptick.serendipity.client.sales.presenter.CalendarPresenter;
import au.com.uptick.serendipity.client.sales.presenter.DashboardsPresenter;
import au.com.uptick.serendipity.client.sales.presenter.ImportsPresenter;
import au.com.uptick.serendipity.client.sales.presenter.ReportsPresenter;
import au.com.uptick.serendipity.client.sales.view.AccountsView;
import au.com.uptick.serendipity.client.sales.view.ActivitiesView;
import au.com.uptick.serendipity.client.sales.view.CalendarView;
import au.com.uptick.serendipity.client.sales.view.DashboardsView;
import au.com.uptick.serendipity.client.sales.view.ImportsView;
import au.com.uptick.serendipity.client.sales.view.ReportsView;
import au.com.uptick.serendipity.client.settings.presenter.AdministrationPresenter;
import au.com.uptick.serendipity.client.settings.view.AdministrationView;
import au.com.uptick.serendipity.client.view.ErrorPageView;
import au.com.uptick.serendipity.client.view.MainPageView;
import au.com.uptick.serendipity.client.view.SignInPageView;
import au.com.uptick.serendipity.shared.SharedTokens;

import com.google.inject.Singleton;
import com.google.gwt.event.shared.EventBus;
import com.google.gwt.event.shared.SimpleEventBus;

import com.gwtplatform.dispatch.shared.SecurityCookie;
import com.gwtplatform.mvp.client.DefaultProxyFailureHandler;
import com.gwtplatform.mvp.client.RootPresenter;
import com.gwtplatform.mvp.client.gin.AbstractPresenterModule;
import com.gwtplatform.mvp.client.proxy.ParameterTokenFormatter;
import com.gwtplatform.mvp.client.proxy.PlaceManager;
import com.gwtplatform.mvp.client.proxy.ProxyFailureHandler;
import com.gwtplatform.mvp.client.proxy.TokenFormatter;

public class ClientModule extends AbstractPresenterModule {

  @Override
  protected void configure() {

    // Protect against XSRF attacks - securityCookieName = "JSESSIONID";
    bindConstant().annotatedWith(SecurityCookie.class).to(SharedTokens.securityCookieName);

    // Singletons
    bind(EventBus.class).to(SimpleEventBus.class).in(Singleton.class);
    bind(PlaceManager.class).to(SerendipityPlaceManager.class).in(Singleton.class);
    bind(TokenFormatter.class).to(ParameterTokenFormatter.class).in(Singleton.class);
    bind(RootPresenter.class).asEagerSingleton();
    bind(ProxyFailureHandler.class).to(DefaultProxyFailureHandler.class).in(Singleton.class);
    
    // bind(Resources.class).in(Singleton.class);
    // bind(Translations.class).in(Singleton.class);
    // bind(CurrentUser.class).asEagerSingleton();  
    
    bind(LoggedInGatekeeper.class).in(Singleton.class);
    bind(AdminGatekeeper.class).in(Singleton.class);

    // Constants
    // Bind the Sign In page to the default place
    bindConstant().annotatedWith(DefaultPlace.class).to(NameTokens.signInPage);

    // Presenters

    // Sign In
    bindPresenter(SignInPagePresenter.class, SignInPagePresenter.MyView.class,
        SignInPageView.class, SignInPagePresenter.MyProxy.class);

    // Main Pages
    bindPresenter(MainPagePresenter.class, MainPagePresenter.MyView.class,
        MainPageView.class, MainPagePresenter.MyProxy.class);
    bindPresenter(AccountPagePresenter.class, AccountPagePresenter.MyView.class,
        AccountPageView.class, AccountPagePresenter.MyProxy.class);
    bindPresenter(FileUploadPagePresenter.class, FileUploadPagePresenter.MyView.class,
        FileUploadPageView.class, FileUploadPagePresenter.MyProxy.class);

    // Error Page
    bindPresenter(ErrorPagePresenter.class, ErrorPagePresenter.MyView.class,
        ErrorPageView.class, ErrorPagePresenter.MyProxy.class);

    // Sales
    bindPresenter(ActivitiesPresenter.class, ActivitiesPresenter.MyView.class,
        ActivitiesView.class, ActivitiesPresenter.MyProxy.class);
    bindPresenter(CalendarPresenter.class, CalendarPresenter.MyView.class,
        CalendarView.class, CalendarPresenter.MyProxy.class);
    bindPresenter(DashboardsPresenter.class, DashboardsPresenter.MyView.class,
        DashboardsView.class, DashboardsPresenter.MyProxy.class);
    bindPresenter(ImportsPresenter.class, ImportsPresenter.MyView.class,
        ImportsView.class, ImportsPresenter.MyProxy.class);
    bindPresenter(AccountsPresenter.class, AccountsPresenter.MyView.class,
        AccountsView.class, AccountsPresenter.MyProxy.class);
    bindPresenter(ReportsPresenter.class, ReportsPresenter.MyView.class,
        ReportsView.class, ReportsPresenter.MyProxy.class);


    bindPresenter(AccountInformationPresenter.class, AccountInformationPresenter.MyView.class,
        AccountInformationView.class, AccountInformationPresenter.MyProxy.class);

    // Settings
    bindPresenter(AdministrationPresenter.class, AdministrationPresenter.MyView.class,
        AdministrationView.class, AdministrationPresenter.MyProxy.class);

    // Resource Centre
    bindPresenter(HighlightsPresenter.class, HighlightsPresenter.MyView.class,
        HighlightsView.class, HighlightsPresenter.MyProxy.class);
  }
}
