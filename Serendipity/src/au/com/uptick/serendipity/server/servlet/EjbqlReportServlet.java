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
import java.util.HashMap;
import java.util.Map;

import javax.persistence.EntityManager;
import javax.persistence.EntityManagerFactory;
import javax.persistence.Persistence;
import javax.servlet.ServletException;
import javax.servlet.ServletOutputStream;
import javax.servlet.http.HttpServlet;
import javax.servlet.http.HttpServletRequest;
import javax.servlet.http.HttpServletResponse;

import net.sf.jasperreports.engine.JRException;
import net.sf.jasperreports.engine.JasperRunManager;
import net.sf.jasperreports.engine.query.JRJpaQueryExecuterFactory;

import com.google.inject.Singleton;

@Singleton
@SuppressWarnings("serial")
public class EjbqlReportServlet extends HttpServlet {

  // <persistence-unit name="au.com.uptick.serendipity" transaction-type="RESOURCE_LOCAL">
  private static final EntityManagerFactory entityManagerFactory =
      Persistence.createEntityManagerFactory("au.com.uptick.serendipity");

  public static EntityManager createEntityManager() {
    return entityManagerFactory.createEntityManager();
  }

  @Override
  protected void doGet(HttpServletRequest request, HttpServletResponse response)
      throws ServletException, IOException {

    EntityManager em = createEntityManager();
    Map<Object, Object> parameterMap = new HashMap<Object, Object>();

    parameterMap.put(JRJpaQueryExecuterFactory.PARAMETER_JPA_ENTITY_MANAGER, em);
    response.setContentType("application/pdf");
    ServletOutputStream servletOutputStream = response.getOutputStream();
    InputStream reportStream = getServletConfig().getServletContext().getResourceAsStream("/reports/AccountsReport.jasper");

    try {
      JasperRunManager.runReportToPdfStream(reportStream, servletOutputStream, parameterMap);

      servletOutputStream.flush();
      servletOutputStream.close();
    }
    catch (JRException ex) {
      // display stack trace in the browser
      StringWriter stringWriter = new StringWriter();
      PrintWriter printWriter = new PrintWriter(stringWriter);
      ex.printStackTrace(printWriter);
      response.setContentType("text/plain");
      response.getOutputStream().print(stringWriter.toString());
    }
    finally {
      if (em != null && em.isOpen()) {
        em.close();
      }
    }
  }
}
