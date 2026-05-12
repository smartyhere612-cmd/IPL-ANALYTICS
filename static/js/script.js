/**
 * IPL Data Analytics — shared frontend behaviour
 * Scroll reveal, counters, navbar, typing effect, loader
 */

(function () {
    "use strict";

    /** Remove full-screen loader after paint */
    function hidePageLoader() {
        var loader = document.getElementById("page-loader");
        if (!loader) return;
        setTimeout(function () {
            loader.classList.add("loader-done");
        }, 450);
    }

    /** IntersectionObserver for fade-up sections */
    function initScrollReveal() {
        var els = document.querySelectorAll(".reveal-up");
        if (!("IntersectionObserver" in window) || !els.length) {
            els.forEach(function (el) {
                el.classList.add("is-visible");
            });
            return;
        }
        var obs = new IntersectionObserver(
            function (entries) {
                entries.forEach(function (entry) {
                    if (entry.isIntersecting) {
                        entry.target.classList.add("is-visible");
                        obs.unobserve(entry.target);
                    }
                });
            },
            { threshold: 0.12, rootMargin: "0px 0px -40px 0px" }
        );
        els.forEach(function (el) {
            obs.observe(el);
        });
    }

    /** Animate numeric counters when visible */
    function animateCounter(el, target, duration) {
        var start = 0;
        var startTime = null;
        function step(ts) {
            if (!startTime) startTime = ts;
            var p = Math.min((ts - startTime) / duration, 1);
            var eased = 1 - Math.pow(1 - p, 3);
            el.textContent = Math.floor(start + (target - start) * eased).toLocaleString();
            if (p < 1) requestAnimationFrame(step);
            else el.textContent = target.toLocaleString();
        }
        requestAnimationFrame(step);
    }

    function initCounters() {
        var counters = document.querySelectorAll(".counter[data-target]");
        if (!("IntersectionObserver" in window)) {
            counters.forEach(function (c) {
                var t = parseInt(c.getAttribute("data-target"), 10);
                if (!isNaN(t)) c.textContent = t.toLocaleString();
            });
            return;
        }
        var obs = new IntersectionObserver(
            function (entries) {
                entries.forEach(function (entry) {
                    if (!entry.isIntersecting) return;
                    var el = entry.target;
                    var target = parseInt(el.getAttribute("data-target"), 10);
                    if (!isNaN(target)) animateCounter(el, target, 1400);
                    obs.unobserve(el);
                });
            },
            { threshold: 0.3 }
        );
        counters.forEach(function (c) {
            obs.observe(c);
        });
    }

    /** Navbar adds shadow class on scroll */
    function initNavbarScroll() {
        var nav = document.querySelector(".ipl-navbar");
        if (!nav) return;
        function onScroll() {
            if (window.scrollY > 24) nav.classList.add("navbar-scrolled");
            else nav.classList.remove("navbar-scrolled");
        }
        onScroll();
        window.addEventListener("scroll", onScroll, { passive: true });
    }

    /** Simple typing effect for elements with .typing-text */
    function initTyping() {
        var el = document.querySelector(".typing-text");
        if (!el) return;
        var full = el.getAttribute("data-text") || "";
        el.textContent = "";
        var i = 0;
        function tick() {
            if (i <= full.length) {
                el.textContent = full.slice(0, i);
                i++;
                setTimeout(tick, 55);
            }
        }
        tick();
    }

    /** Footer year */
    function setYear() {
        var y = document.getElementById("year-copy");
        if (y) y.textContent = new Date().getFullYear();
    }

    /** Auto-dismiss Bootstrap flash alerts */
    function autoDismissAlerts() {
        var alerts = document.querySelectorAll(".flash-stack .alert");
        alerts.forEach(function (a) {
            setTimeout(function () {
                a.style.opacity = "0";
                a.style.transform = "translateY(-8px)";
                setTimeout(function () {
                    a.remove();
                }, 400);
            }, 5000);
        });
    }

    /**
     * Dashboard mobile drawer: close offcanvas on in-app navigation without blocking <a href>.
     * data-bs-dismiss on anchor tags can prevent navigation on some mobile browsers.
     */
    function initDashOffcanvasNav() {
        var drawer = document.getElementById("dashDrawer");
        if (!drawer || typeof bootstrap === "undefined") return;
        drawer.querySelectorAll("a.dash-offcanvas-link[href]").forEach(function (link) {
            link.addEventListener(
                "click",
                function () {
                    var inst = bootstrap.Offcanvas.getInstance(drawer);
                    if (inst) inst.hide();
                },
                { passive: true }
            );
        });
    }

    document.addEventListener("DOMContentLoaded", function () {
        hidePageLoader();
        initScrollReveal();
        initCounters();
        initNavbarScroll();
        initTyping();
        setYear();
        autoDismissAlerts();
        initDashOffcanvasNav();
    });
})();
