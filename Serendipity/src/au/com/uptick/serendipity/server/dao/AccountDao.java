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

import au.com.uptick.serendipity.server.domain.Account;

public class AccountDao extends BaseDao {

  public Long createObject(Object object) {
    return createAccount((Account) object);
  }

  public List<Object> retrieveObjects(int maxResults, int firstResult) {

    EntityManager em = createEntityManager();
    List<Object> list = null;

    try {
      TypedQuery<Object> query = em.createQuery("select a from Account a", Object.class);
      query.setMaxResults(maxResults);
      query.setFirstResult(firstResult);
      list = query.getResultList();
    }
    finally {
      em.close();
    }

    return list;
  }

  public Long createAccount(Account account) {

    // For an application-managed entity manager its best practice to create a
    // new entity manager inside a method and close it before the method is finished.

    EntityManager em = createEntityManager();
    EntityTransaction tx = em.getTransaction();
    Long accountId = -1L;

    try {
      tx.begin();
      em.persist(account);
      accountId = account.getAccountId();
      tx.commit();
    }
    catch (Throwable t) {
      t.printStackTrace();
      tx.rollback();
    }
    finally {
      em.close();
    }

    return accountId;
  }

  public Account retrieveAccount(Long accountId) {

    EntityManager em = createEntityManager();
    Account account = null;

    try {
      TypedQuery<Account> query = em.createQuery("select a from Account a where a.accountId = ?1", Account.class);
      query.setParameter(1, accountId);
      account = query.getSingleResult();
    }
    finally {
      em.close();
    }

    return account;
  }

  public List<Account> retrieveAccounts(int maxResults, int firstResult) {

    EntityManager em = createEntityManager();
    List<Account> list = null;

    try {
      TypedQuery<Account> query = em.createQuery("select a from Account a", Account.class);
      query.setMaxResults(maxResults);
      query.setFirstResult(firstResult);
      list = query.getResultList();
    }
    finally {
      em.close();
    }

    return list;
  }

  public Account updateAccount(Account account) {

    EntityManager em = createEntityManager();
    EntityTransaction tx = em.getTransaction();
    Account account2 = null;

    try {
      tx.begin();
      account2 = em.merge(account);
      tx.commit();
    }
    catch (Throwable t) {
      t.printStackTrace();
      tx.rollback();
    }
    finally {
      em.close();
    }

    return account2;
  }

  public void deleteAccount(Account account) {

    EntityManager em = createEntityManager();
    EntityTransaction tx = em.getTransaction();

    try {
      tx.begin();
      em.remove(em.merge(account));
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
