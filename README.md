# DNS

## Задание

1. Добавить еще один сервер **client2**.
2. Завести в зоне **dns.lab** имена:

    - **web1** - смотрит на **client1**;
    - **web2** - смотрит на **client2**.

3. Завести еще одну зону **newdns.lab**. Завести в ней запись **www**, которая смотрит на обоих клиентов.

4. Настроить **split-dns**:

    - **client1** видит обе зоны, но в зоне **dns.lab** только **web1**.
    - **client2** видит только **dns.lab**.

5. Настроить всё без выключения **SELinux**.

## Реализация

Задание сделано на **rockylinux/9** версии **v4.0.0**. Для автоматизации процесса написан **Ansible Playbook** [playbook.yml](playbook.yml) который последовательно запускает следующие роли:

- **disable_ipv6** - отключает на серверах **IPv6**, так как с ним не работает **DNSSEC**, ввиду того, что **bind** не может получить ключи по этому протоколу с ошибкой `managed-keys-zone: Unable to fetch DNSKEY set '.': timed out`, из-за чего с включённым **DNSSEC** сервер не может обрабатывать рекурсивные запросы.
- **bind** - настраивает **bind** согласно шаблону конфигурации [named.conf](roles/bind/templates/named.conf). Файлы зон приведены в директории [templates/zones](roles/bind/templates/zones/) роли. Перменные указаны в [host_vars](host_vars/), [group_vars/all.yml](group_vars/all.yml), [defaults](roles/bind/defaults/main.yml).
- **resolv** - заполняет файл `/etc/resolv.conf` значениями из переменных **resolv_domain**, **resolv_search**, **resolv_nameservers** в [group_vars/all.yml](group_vars/all.yml).
- **motd** - настраивает сообщение при подключении к **SSH** на клиентах по шаблону [dns.lab](roles/motd/templates/dns.lab).

Дополнительно написан **filter_plugin** для **Ansible** позволяющий конвертировать бинарные данные в виде **hex** строки в **base64** кодироку (именно бинарный данные, а не саму строку) - [hex2b64.py](filter_plugins/hex2b64.py).

Для каждого сервера с помощью **ansible** генерится свой ключ, в результате **bind** может идентифицировать сервер по этому ключу. Ключи **client1** и **client2** используются также для идентификации запросов к определённому **view** с помощью **ACL**. Все зоны **ns02** и зону внутри **view** сервера **ns01** (кроме зоны **dns.lab** внутри **client1 view**) настроены, как **secondary**. Для зоны **ddns.lab** настроена опция **allow_update_forwarding**, которая позволяет перенаправлять запросы на обновления на **master** сервера. Чтобы сервер **ns01** мог получить свои **secondary** зоны с ебя, он настроен (внутри **view** **client1** и **client2**), как **127.0.0.1** и это адрес добавлен в исключения **ACL**.

Все файлы перемещены в правильные директории, поэтому **SELinux** не мешает работе **bind**.

Итоговая конфигурация доступна в директории **configs**:

- [ns01.conf](configs/ns01.conf)
- [ns02.conf](configs/ns02.conf)

## Запуск

Необходимо скачать **VagrantBox** для **rockylinux/9** версии **v4.0.0** и добавить его в **Vagrant** под именем **rockylinux/9/v4.0.0**. Сделать это можно командами:

```shell
curl -OL https://app.vagrantup.com/rockylinux/boxes/9/versions/4.0.0/providers/virtualbox/amd64/vagrant.box
vagrant box add vagrant.box --name "rockylinux/9/v4.0.0"
rm vagrant.box
```

Для того, чтобы **vagrant 2.3.7** работал с **VirtualBox 7.1.0** необходимо добавить эту версию в **driver_map** в файле **/usr/share/vagrant/gems/gems/vagrant-2.3.7/plugins/providers/virtualbox/driver/meta.rb**:

```ruby
          driver_map   = {
            "4.0" => Version_4_0,
            "4.1" => Version_4_1,
            "4.2" => Version_4_2,
            "4.3" => Version_4_3,
            "5.0" => Version_5_0,
            "5.1" => Version_5_1,
            "5.2" => Version_5_2,
            "6.0" => Version_6_0,
            "6.1" => Version_6_1,
            "7.0" => Version_7_0,
            "7.1" => Version_7_0,
          }
```

После этого нужно сделать **vagrant up**.

Протестировано в **OpenSUSE Tumbleweed**:

- **Vagrant 2.3.7**
- **VirtualBox 7.1.4_SUSE r165100**
- **Ansible 2.17.6**
- **Python 3.11.10**
- **Jinja2 3.1.4**

## Проверка

Проверим доступность имён **web1.dns.lab** и **web2.dns.lab** на **ns01** и **ns02** с **client1**:

```shell
[vagrant@client1 ~]$ dig @192.168.50.10 +noall +answer web1.dns.lab
web1.dns.lab.           3600    IN      A       192.168.50.15
[vagrant@client1 ~]$ dig @192.168.50.11 +noall +answer web1.dns.lab
web1.dns.lab.           3600    IN      A       192.168.50.15
[vagrant@client1 ~]$ dig @192.168.50.10 +noall +answer web2.dns.lab
[vagrant@client1 ~]$ dig @192.168.50.11 +noall +answer web2.dns.lab
```

Проверим доступность имён **web1.dns.lab** и **web2.dns.lab** на **ns01** и **ns02** с **client2**:

```shell
[vagrant@client2 ~]$ dig @192.168.50.10 +noall +answer web1.dns.lab
web1.dns.lab.           3600    IN      A       192.168.50.15
[vagrant@client2 ~]$ dig @192.168.50.11 +noall +answer web1.dns.lab
web1.dns.lab.           3600    IN      A       192.168.50.15
[vagrant@client2 ~]$ dig @192.168.50.10 +noall +answer web2.dns.lab
web2.dns.lab.           3600    IN      A       192.168.50.16
[vagrant@client2 ~]$ dig @192.168.50.11 +noall +answer web2.dns.lab
web2.dns.lab.           3600    IN      A       192.168.50.16
```

Проверим доступность имени **www.newdns.lab** с **client1**:

```shell
[vagrant@client1 ~]$ dig @192.168.50.10 +noall +answer www.newdns.lab
www.newdns.lab.         3600    IN      A       192.168.50.16
www.newdns.lab.         3600    IN      A       192.168.50.15
[vagrant@client1 ~]$ dig @192.168.50.11 +noall +answer www.newdns.lab
www.newdns.lab.         3600    IN      A       192.168.50.15
www.newdns.lab.         3600    IN      A       192.168.50.16
```

Проверим доступность имени **www.newdns.lab** с **client2**:

```shell
[vagrant@client2 ~]$ dig @192.168.50.10 +noall +answer www.newdns.lab
[vagrant@client2 ~]$ dig @192.168.50.11 +noall +answer www.newdns.lab
```

Как видно задание выполнено, однако дополнительно проверим работу рекурсии, **DDNS** и доступность других зон.

Отправим рекурсивные запрос к **yandex.ru**, **rutube.ru** в **default view** на сервера **ns01** и **ns02**:

```shell
[vagrant@ns02 ~]$ dig @192.168.50.10 +noall +answer yandex.ru
yandex.ru.              600     IN      A       77.88.55.88
yandex.ru.              600     IN      A       5.255.255.77
yandex.ru.              600     IN      A       77.88.44.55
[vagrant@ns02 ~]$ dig @192.168.50.11 +noall +answer rutube.ru
rutube.ru.              300     IN      A       178.248.233.148
rutube.ru.              300     IN      A       109.238.90.239
```

Отправим рекурсивные запрос к **google.com**, **youtube.com** в **client1 view** на сервера **ns01** и **ns02**:

```shell
[vagrant@client1 ~]$ dig @192.168.50.10 +noall +answer google.com
google.com.             300     IN      A       142.250.150.138
google.com.             300     IN      A       142.250.150.101
google.com.             300     IN      A       142.250.150.102
google.com.             300     IN      A       142.250.150.139
google.com.             300     IN      A       142.250.150.113
google.com.             300     IN      A       142.250.150.100
[vagrant@client1 ~]$ dig @192.168.50.11 +noall +answer youtube.com
youtube.com.            300     IN      A       142.251.1.190
youtube.com.            300     IN      A       142.251.1.91
youtube.com.            300     IN      A       142.251.1.93
youtube.com.            300     IN      A       142.251.1.136
```

Отправим рекурсивные запрос к **wikipedia.org**, **t.me** в **client2 view** на сервера **ns01** и **ns02**:

```shell
[vagrant@client2 ~]$ dig @192.168.50.10 +noall +answer wikipedia.org
wikipedia.org.          295     IN      A       185.15.59.224
[vagrant@client2 ~]$ dig @192.168.50.11 +noall +answer t.me
t.me.                   56      IN      A       149.154.167.99
```

Для проверки работы **DDNS** будем использовать **secondary** сервер **ns02**, таким образом запрос на обновление зоны пойдёт по пути **ns02** -> **ns01** -> **127.0.0.1** -> **ns01** -> **ns02**:

Проверим работу **DDNS** с **client1**:

```shell
[vagrant@client1 ~]$ nsupdate -k /etc/named/client1.key
> server 192.168.50.11
> zone ddns.lab
> update add client1.ddns.lab. 60 A 192.168.50.15
> send
```

```shell
[vagrant@client2 ~]$ nsupdate -k /etc/named/client2.key
> server 192.168.50.11
> zone ddns.lab
> update add client2.ddns.lab. 60 A 192.168.50.16
> send
```

Проверим, что имена **client1.ddns.lab** и **client2.ddns.lab** разрешаются из **default view**:

```shell
vagrant@ns02 ~]$ dig @192.168.50.10 +noall +answer client1.ddns.lab
client1.ddns.lab.       60      IN      A       192.168.50.15
[vagrant@ns02 ~]$ dig @192.168.50.10 +noall +answer client2.ddns.lab
client2.ddns.lab.       60      IN      A       192.168.50.16
[vagrant@ns02 ~]$ dig @192.168.50.11 +noall +answer client1.ddns.lab
client1.ddns.lab.       60      IN      A       192.168.50.15
[vagrant@ns02 ~]$ dig @192.168.50.11 +noall +answer client2.ddns.lab
client2.ddns.lab.       60      IN      A       192.168.50.16
```

Проверим, что имена **client1.ddns.lab** и **client2.ddns.lab** разрешаются из **client1 view**:

```shell
[vagrant@client1 ~]$ dig @192.168.50.10 +noall +answer client1.ddns.lab
client1.ddns.lab.       60      IN      A       192.168.50.15
[vagrant@client1 ~]$ dig @192.168.50.10 +noall +answer client2.ddns.lab
client2.ddns.lab.       60      IN      A       192.168.50.16
[vagrant@client1 ~]$ dig @192.168.50.11 +noall +answer client1.ddns.lab
client1.ddns.lab.       60      IN      A       192.168.50.15
[vagrant@client1 ~]$ dig @192.168.50.11 +noall +answer client2.ddns.lab
client2.ddns.lab.       60      IN      A       192.168.50.16
```

Проверим, что имена **client1.ddns.lab** и **client2.ddns.lab** разрешаются из **client2 view**:

```shell
[vagrant@client2 ~]$ dig @192.168.50.10 +noall +answer client1.ddns.lab
client1.ddns.lab.       60      IN      A       192.168.50.15
[vagrant@client2 ~]$ dig @192.168.50.10 +noall +answer client2.ddns.lab
client2.ddns.lab.       60      IN      A       192.168.50.16
[vagrant@client2 ~]$ dig @192.168.50.11 +noall +answer client1.ddns.lab
client1.ddns.lab.       60      IN      A       192.168.50.15
[vagrant@client2 ~]$ dig @192.168.50.11 +noall +answer client2.ddns.lab
client2.ddns.lab.       60      IN      A       192.168.50.16
```

Проверим работу остальных зон в **default view**:

```shell
[vagrant@ns02 ~]$ dig @192.168.50.10 +noall +answer web1.dns.lab
web1.dns.lab.           3600    IN      A       192.168.50.15
[vagrant@ns02 ~]$ dig @192.168.50.11 +noall +answer web1.dns.lab
web1.dns.lab.           3600    IN      A       192.168.50.15
[vagrant@ns02 ~]$ dig @192.168.50.10 +noall +answer www.newdns.lab
www.newdns.lab.         3600    IN      A       192.168.50.16
www.newdns.lab.         3600    IN      A       192.168.50.15
[vagrant@ns02 ~]$ dig @192.168.50.11 +noall +answer www.newdns.lab
www.newdns.lab.         3600    IN      A       192.168.50.16
www.newdns.lab.         3600    IN      A       192.168.50.15
[vagrant@ns02 ~]$ dig @192.168.50.10 +noall +answer -x 192.168.50.10
10.50.168.192.in-addr.arpa. 3600 IN     PTR     ns01.dns.lab.
[vagrant@ns02 ~]$ dig @192.168.50.11 +noall +answer -x 192.168.50.10
10.50.168.192.in-addr.arpa. 3600 IN     PTR     ns01.dns.lab.
```

Проверим работу остальных зон в **client1 view**:

```shell
[vagrant@client1 ~]$ dig @192.168.50.10 +noall +answer web1.dns.lab
web1.dns.lab.           3600    IN      A       192.168.50.15
[vagrant@client1 ~]$ dig @192.168.50.11 +noall +answer web1.dns.lab
web1.dns.lab.           3600    IN      A       192.168.50.15
[vagrant@client1 ~]$ dig @192.168.50.10 +noall +answer www.newdns.lab
www.newdns.lab.         3600    IN      A       192.168.50.15
www.newdns.lab.         3600    IN      A       192.168.50.16
[vagrant@client1 ~]$ dig @192.168.50.11 +noall +answer www.newdns.lab
www.newdns.lab.         3600    IN      A       192.168.50.16
www.newdns.lab.         3600    IN      A       192.168.50.15
[vagrant@client1 ~]$ dig @192.168.50.10 +noall +answer -x 192.168.50.10
10.50.168.192.in-addr.arpa. 3600 IN     PTR     ns01.dns.lab.
[vagrant@client1 ~]$ dig @192.168.50.11 +noall +answer -x 192.168.50.10
10.50.168.192.in-addr.arpa. 3600 IN     PTR     ns01.dns.lab.
```

Проверим работу остальных зон в **client2 view**:

```shell
[vagrant@client2 ~]$ dig @192.168.50.10 +noall +answer web1.dns.lab
web1.dns.lab.           3600    IN      A       192.168.50.15
[vagrant@client2 ~]$ dig @192.168.50.11 +noall +answer web1.dns.lab
web1.dns.lab.           3600    IN      A       192.168.50.15
[vagrant@client2 ~]$ dig @192.168.50.10 +noall +answer www.newdns.lab
[vagrant@client2 ~]$ dig @192.168.50.11 +noall +answer www.newdns.lab
[vagrant@client2 ~]$ dig @192.168.50.10 +noall +answer -x 192.168.50.10
10.50.168.192.in-addr.arpa. 3600 IN     PTR     ns01.dns.lab.
[vagrant@client2 ~]$ dig @192.168.50.11 +noall +answer -x 192.168.50.10
10.50.168.192.in-addr.arpa. 3600 IN     PTR     ns01.dns.lab.
```

Зона **newdns.lab** не работает в **client2 view**, так как это требовалось в задании.
