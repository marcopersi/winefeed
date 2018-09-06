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

import au.com.uptick.serendipity.server.domain.User;

public class UserDao extends BaseDao {

  public Long createObject(Object object) {
    return null;
  }

  @Override
  public List<Object> retrieveObjects(int maxResults, int firstResult) {
    return null;
  }

  public String createUser(User user) {

    EntityManager em = createEntityManager();
    EntityTransaction tx = em.getTransaction();
    String login = "";

    try {
      tx.begin();
      em.persist(user);
      login = user.getLogin();
      tx.commit();
    }
    catch (Throwable t) {
      t.printStackTrace();
      tx.rollback();
    }
    finally {
      em.close();
    }

    return login;
  }

  // e.g. UserDetails loadUserByUsername(String username)

  public User retrieveUser(String login) {

    EntityManager em = createEntityManager();
    User user = null;

    try {
      TypedQuery<User> query = em.createQuery("select u from User u where u.login = ?1", User.class);
      query.setParameter(1, login);
      user = query.getSingleResult();
    }
    finally {
      em.close();
    }

    return user;
  }
}
