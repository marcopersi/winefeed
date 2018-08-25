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

package au.com.uptick.serendipity.server.guice;

import au.com.uptick.serendipity.server.servlet.FileDownloadServlet;
import au.com.uptick.serendipity.server.servlet.FileUploadServlet;
import au.com.uptick.serendipity.server.servlet.ReportServlet;
import au.com.uptick.serendipity.shared.SharedTokens;

import com.google.inject.servlet.ServletModule;
import com.gwtplatform.dispatch.server.guice.DispatchServiceImpl;
import com.gwtplatform.dispatch.shared.ActionImpl;
import com.gwtplatform.dispatch.shared.SecurityCookie;

public class DispatchServletModule extends ServletModule {

  @Override
  public void configureServlets() {
    bindConstants();
    bindFilters();
    bindServlets();
  }

  protected void bindConstants() {
    // Protect against XSRF attacks - securityCookieName = "JSESSIONID";
    bindConstant().annotatedWith(SecurityCookie.class).to(SharedTokens.securityCookieName);
  }

  protected void bindFilters() {
  }

  /*

  protected void bindServlets() {
    // For GWT 2.0.4
    serve("/serendipity/" + ActionImpl.DEFAULT_SERVICE_NAME).with(
        DispatchServiceImpl.class);
  }

  */

  // <!--
  // This Guice listener hijacks all further filters and servlets.
  // Extra filters and servlets have to be configured in your
  // ServletModule#configureServlets() by calling
  // serve(String).with(Class<? extends HttpServlet>) and
  // filter(String).through(Class<? extends Filter).
  // -->

  public static final String DEFAULT_SERVICE_PATH = "/";
  public static final String REPORTS_SERVICE_PATH = "/reports/*";
  public static final String FILE_UPLOAD_SERVICE_PATH = "/upload";
  public static final String FILE_DOWNLOAD_SERVICE_PATH = "/download/*";

  protected void bindServlets() {
    // For GWT 2.1.1
    serve(DEFAULT_SERVICE_PATH + ActionImpl.DEFAULT_SERVICE_NAME).with(
        DispatchServiceImpl.class);

    // This registers a servlet (subclass of HttpServlet) called ReportServlet
    // to serve any web requests using a path-style syntax (as you would in web.xml).
    serve(REPORTS_SERVICE_PATH).with(ReportServlet.class);
    serve(FILE_UPLOAD_SERVICE_PATH).with(FileUploadServlet.class);
    serve(FILE_DOWNLOAD_SERVICE_PATH).with(FileDownloadServlet.class);
  }
}
