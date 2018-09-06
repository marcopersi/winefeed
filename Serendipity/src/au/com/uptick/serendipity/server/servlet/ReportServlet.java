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

package au.com.uptick.serendipity.server.servlet;

import java.io.IOException;
import java.io.InputStream;
import java.io.PrintWriter;
import java.io.StringWriter;
import java.sql.Connection;
import java.sql.DriverManager;
import java.util.HashMap;

import javax.servlet.ServletException;
import javax.servlet.ServletOutputStream;
import javax.servlet.http.HttpServlet;
import javax.servlet.http.HttpServletRequest;
import javax.servlet.http.HttpServletResponse;

import net.sf.jasperreports.engine.JasperRunManager;

import com.allen_sauer.gwt.log.client.Log;
import com.google.inject.Singleton;

@Singleton
@SuppressWarnings("serial")
public class ReportServlet extends HttpServlet {

  // as per ReportsRecord
  private static final String REPORT_FILENAME = "reportFilename";
  private static final String DEFAULT_REPORTS_SERVICE_PATH = "/reports/";

  @Override
  public void doGet(HttpServletRequest request, HttpServletResponse response)
      throws ServletException, IOException {
    this.processRequest(request, response);
  }

  @Override
  public void doPost(HttpServletRequest request, HttpServletResponse response)
      throws ServletException, IOException {
    this.processRequest(request, response);
  }

  private void processRequest(HttpServletRequest request, HttpServletResponse response)
      throws ServletException, IOException {

    Log.info("Report Servlet");

    String reportFilename = request.getParameter(REPORT_FILENAME);
    String resourceName = DEFAULT_REPORTS_SERVICE_PATH + reportFilename;

    response.setContentType("application/pdf");
    ServletOutputStream servletOutputStream = response.getOutputStream();
    InputStream reportStream = getServletConfig().getServletContext().getResourceAsStream(resourceName);

    try {
      // Class.forName("org.hsqldb.jdbcDriver");
      Connection connection = DriverManager.getConnection("jdbc:hsqldb:file:/db/serendipitydb",
          "sa", "");

      JasperRunManager.runReportToPdfStream(reportStream, servletOutputStream,
          new HashMap<Object, Object>(), connection);

      connection.close();
    }
    catch (Exception e) {
      // display stack trace in the browser
      StringWriter stringWriter = new StringWriter();
      PrintWriter printWriter = new PrintWriter(stringWriter);
      e.printStackTrace(printWriter);
      response.setContentType("text/plain");
      response.getOutputStream().print(stringWriter.toString());
    }
    finally {
      servletOutputStream.flush();
      servletOutputStream.close();
    }
  }
}

/*


  protected void handleSubmit(HttpServletRequest request, HttpServletResponse response)
      throws ServletException, IOException {

    DOMConfigurator.configure("log4j.xml");

    Log.info("Report Servlet");

    String reportFilename = request.getParameter(REPORT_FILENAME);

    // String resourceName = request.getSession().getServletContext().getRealPath("/") +
    //     DEFAULT_REPORTS_SERVICE_PATH + reportFilename;
    // Log.info("resourceName: " + resourceName);

    response.setContentType("application/pdf");
    ServletOutputStream servletOutputStream = response.getOutputStream();
    InputStream reportStream = getServletConfig().getServletContext().getResourceAsStream(DEFAULT_REPORTS_SERVICE_PATH + reportFilename);
    // InputStream reportStream = getServletConfig().getServletContext().getResourceAsStream(resourceName);

    // Connection connection;

    try {
      // Class.forName("org.hsqldb.jdbcDriver");
      Connection connection = DriverManager.getConnection("jdbc:hsqldb:file:/db/serendipitydb", "sa", "");

      JasperRunManager.runReportToPdfStream(reportStream, servletOutputStream,
          new HashMap<Object, Object>(), connection);

      connection.close();
    }
    catch (Exception e) {
      // display stack trace in the browser
      StringWriter stringWriter = new StringWriter();
      PrintWriter printWriter = new PrintWriter(stringWriter);
      e.printStackTrace(printWriter);
      response.setContentType("text/plain");
      response.getOutputStream().print(stringWriter.toString());
    }
    finally {
      servletOutputStream.flush();
      servletOutputStream.close();
    }
  }



@Singleton
@SuppressWarnings("serial")
public class ReportServlet extends HttpServlet
{

  @Override
  protected void doGet(HttpServletRequest request, HttpServletResponse response)
      throws ServletException, IOException
  {
    ServletOutputStream servletOutputStream = response.getOutputStream();
    InputStream reportStream = getServletConfig().getServletContext()
        .getResourceAsStream("/reports/AccountsReport.jasper");

    try
    {
      JasperRunManager.runReportToPdfStream(reportStream, servletOutputStream,
          new HashMap<Object, Object>(), new JREmptyDataSource());

      response.setContentType("application/pdf");
      servletOutputStream.flush();
      servletOutputStream.close();
    }
    catch (JRException e)
    {
      // display stack trace in the browser
      StringWriter stringWriter = new StringWriter();
      PrintWriter printWriter = new PrintWriter(stringWriter);
      e.printStackTrace(printWriter);
      response.setContentType("text/plain");
      response.getOutputStream().print(stringWriter.toString());
    }
  }
}

*/