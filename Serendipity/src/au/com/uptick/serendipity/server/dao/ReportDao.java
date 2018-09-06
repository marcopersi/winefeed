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

package au.com.uptick.serendipity.server.dao;

import java.util.List;

import javax.persistence.EntityManager;
import javax.persistence.EntityTransaction;
import javax.persistence.TypedQuery;

import au.com.uptick.serendipity.server.domain.Report;

public class ReportDao extends BaseDao {

  public Long createObject(Object object) {
    return createReport((Report) object);
  }

  public List<Object> retrieveObjects(int maxResults, int firstResult) {

    EntityManager em = createEntityManager();
    List<Object> list = null;

    try {
      TypedQuery<Object> query = em.createQuery("select a from Report a", Object.class);
      query.setMaxResults(maxResults);
      query.setFirstResult(firstResult);
      list = query.getResultList();
    }
    finally {
      em.close();
    }

    return list;
  }

  public Long createReport(Report report) {

    EntityManager em = createEntityManager();
    EntityTransaction tx = em.getTransaction();
    Long reportId = -1L;

    try {
      tx.begin();
      em.persist(report);
      reportId = report.getReportId();
      tx.commit();
    }
    catch (Throwable t) {
      t.printStackTrace();
      tx.rollback();
    }
    finally {
      em.close();
    }

    return reportId;
  }

  public Report retrieveReport(Long reportId) {

    EntityManager em = createEntityManager();
    Report report = null;

    try {
      TypedQuery<Report> query = em.createQuery("select a from Report a where a.reportId = ?1", Report.class);
      query.setParameter(1, reportId);
      report = query.getSingleResult();
    }
    finally {
      em.close();
    }

    return report;
  }

  public List<Report> retrieveReports(int maxResults, int firstResult) {

    EntityManager em = createEntityManager();
    List<Report> list = null;

    try {
      TypedQuery<Report> query = em.createQuery("select a from Report a", Report.class);
      query.setMaxResults(maxResults);
      query.setFirstResult(firstResult);
      list = query.getResultList();
    }
    finally {
      em.close();
    }

    return list;
  }

  public Report updateReport(Report report) {

    EntityManager em = createEntityManager();
    EntityTransaction tx = em.getTransaction();
    Report report2 = null;

    try {
      tx.begin();
      report2 = em.merge(report);
      tx.commit();
    }
    catch (Throwable t) {
      t.printStackTrace();
      tx.rollback();
    }
    finally {
      em.close();
    }

    return report2;
  }

  public void deleteReport(Report report) {

    EntityManager em = createEntityManager();
    EntityTransaction tx = em.getTransaction();

    try {
      tx.begin();
      em.remove(em.merge(report));
      tx.commit();
    }
    catch (Throwable t) {
      t.printStackTrace();
      tx.rollback();
    }
    finally {
      em.close();
    }
  }
}
